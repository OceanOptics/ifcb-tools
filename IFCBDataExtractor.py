# Generate PNG and metadata from raw IFCB data and environmental data file

import pandas as pd
from pandas.api.types import union_categoricals
import numpy as np
import os, glob
from PIL import Image
import matlab.engine
from tqdm import tqdm


ADC_COLUMN_NAMES = ['TriggerId', 'ADCTime', 'SSCIntegrated', 'FLIntegrated', 'PMTC', 'PMTD', 'SSCPeak', 'FLPeak', 'PeakC', 'PeakD',
                    'TimeOfFlight', 'GrabTimeStart', 'GrabTimeEnd', 'ImageX', 'ImageY', 'ImageWidth', 'ImageHeight', 'StartByte',
                    'ComparatorOut', 'StartPoint', 'SignalLength', 'Status', 'RunTime', 'InhibitTime']
ADC_COLUMN_SEL = ['SSCIntegrated', 'FLIntegrated', 'SSCPeak', 'FLPeak', 'TimeOfFlight',
                  'ImageX', 'ImageY', 'ImageWidth', 'ImageHeight', 'NumberImagesInTrigger']
HDR_COLUMN_NAMES = ['VolumeSampled', 'VolumeSampleRequested',
                    'TriggerSelection', 'SSCGain', 'FLGain', 'SSCThreshold', 'FLThreshold']
FTR_V2_COLUMN_NAMES = ['ImageId', 'Area', 'NumberBlobsInImage',
                    'EquivalentDiameter', 'FeretDiameter', 'MinorAxisLength', 'MajorAxisLength', 'Perimeter', 'Biovolume',
                    'TextureContrast', 'TextureGrayLevel', 'TextureEntropy', 'TextureSmoothness', 'TextureUniformity']
FTR_V4_COLUMN_NAMES = ['ImageId', 'Area', 'NumberBlobsInImage', 'EquivalentDiameter', 'MinFeretDiameter', 'MaxFeretDiameter',
                       'MinorAxisLength', 'MajorAxisLength', 'Perimeter', 'Biovolume', 'ConvexArea', 'ConvexPerimeter',
                       'SurfaceArea', 'Eccentricity', 'Extent', 'Orientation', 'RepresentativeWidth', 'Solidity']
PATH_TO_IFCB_ANALYSIS_V2 = '/Users/nils/Documents/MATLAB/easyIFCB/IFCB_analysis/'
PATH_TO_IFCB_ANALYSIS_V3 = '/Users/nils/Documents/MATLAB/easyIFCB/IFCB_analysis_v3/'
PATH_TO_DIPUM = '/Users/nils/Documents/MATLAB/easyIFCB/DIPUM/'
PATH_TO_EASY_IFCB = '/Users/nils/Documents/MATLAB/easyIFCB/'

FLOWRATE = 0.25

class BinExtractor:

    def __init__(self, path_to_bin, path_to_output, path_to_environmental_csv=None,
                 path_to_ecotaxa_tsv=None, path_to_taxonomic_grouping_csv=None,
                 matlab_engine=None, matlab_parallel_flag=False):
        self.path_to_bin = path_to_bin
        self.path_to_output = path_to_output
        self.matlab_engine = matlab_engine
        self.matlab_parallel_flag = matlab_parallel_flag
        if path_to_environmental_csv:
            #   the environmental file must be in csv format and the first line must be the column names
            #   one of the column must be named "bin" and contain the bin id: D<yyyymmdd>T<HHMMSS>_IFCB<SN#>
            self.environmental_data = pd.read_csv(path_to_environmental_csv, header=0, engine='c')
            if 'bin' not in self.environmental_data:
                raise ValueError('Missing column bin in environmental data file.')
        else:
            self.environmental_data = None
        self.classification_data = None
        if path_to_ecotaxa_tsv and path_to_taxonomic_grouping_csv:
            self.initEcoTaxaClassification(path_to_ecotaxa_tsv, path_to_taxonomic_grouping_csv)

    def __del__(self):
        if self.matlab_engine is not None:
            self.matlab_engine.quit()

    def extractImagesAndCytometricData(self, bin_name, write_image=True):
        if not os.path.exists(self.path_to_output):
            os.makedirs(self.path_to_output)
        path_to_png = os.path.join(self.path_to_output, bin_name)
        # Parse ADC File
        adc = pd.read_csv(os.path.join(self.path_to_bin, bin_name + '.adc'), names=ADC_COLUMN_NAMES, engine='c',
                          na_values='-999.00000')
        adc.index = adc.index + 1  # increment index to match feature id
        adc['EndByte'] = adc['StartByte'] + adc['ImageWidth'] * adc['ImageHeight']
        # Get Number of ROI within one trigger
        adc['NumberImagesInTrigger'] = [sum(adc['TriggerId'] == x) for x in adc['TriggerId']]
        rows_to_remove = list()
        if write_image:
            # Open ROI File
            roi = np.fromfile(os.path.join(self.path_to_bin, bin_name + '.roi'), 'uint8')
            bin_name_parts = bin_name.split('_')
            if not os.path.isdir(path_to_png):
                os.mkdir(path_to_png)
            for d in adc.itertuples():
                if d.StartByte != d.EndByte:
                    # Save Image
                    img = roi[d.StartByte:d.EndByte].reshape(d.ImageHeight, d.ImageWidth)
                    # Save with ImageIO (slower)
                    # imageio.imwrite(os.path.join(path_to_png, '%s%sP%05d.png' % (bin_name_parts[1], bin_name_parts[0], d.Index)), img)
                    # Save with PILLOW
                    Image.fromarray(img).save(
                        os.path.join(path_to_png, '%s%sP%05d.png' % (bin_name_parts[1], bin_name_parts[0], d.Index)),
                        'PNG')
                else:
                    # Record lines to remove from adc
                    # rows_to_remove.append(d.Index)
                    adc.drop(index=d.Index, inplace=True)
        else:
            for d in adc.itertuples():
                if d.StartByte == d.EndByte:
                    # Record lines to remove from adc
                    adc.drop(index=d.Index, inplace=True)
        # Keep only columns of interest
        adc = adc[ADC_COLUMN_SEL].astype({'NumberImagesInTrigger': 'uint8'})
        return adc

    def extractBinHeader(self, bin_name):
        # Parse hdr file
        hdr = dict()
        with open(os.path.join(self.path_to_bin, bin_name + '.hdr')) as myfile:
            for line in myfile:
                name, var = line.partition(":")[::2]
                hdr[name.strip()] = var
        # Compute volume sampled
        look_time = float(hdr['runTime']) - float(hdr['inhibitTime'])   # seconds
        volume_sampled = FLOWRATE * look_time / 60
        # Format in Panda DataFrame
        hdr = pd.DataFrame([[volume_sampled, float(hdr['SyringeSampleVolume']),
                             int(hdr['PMTtriggerSelection_DAQ_MCConly']),
                             float(hdr['PMTAhighVoltage']), float(hdr['PMTBhighVoltage']),
                             float(hdr['PMTAtriggerThreshold_DAQ_MCConly']), float(hdr['PMTBtriggerThreshold_DAQ_MCConly'])]],
                           columns=HDR_COLUMN_NAMES)
        return hdr

    def extractFeatures_v2(self, bin_name, minimal_feature_flag=False):
        """ Extract features using a custom function (fastFeatureExtration)
            based on the ifcb-analysis main branch (default) """
        if self.matlab_engine is None:
            # Start Matlab engine and add IFCB_analysis
            self.matlab_engine = matlab.engine.start_matlab()

        self.matlab_engine.addpath(os.path.join(PATH_TO_IFCB_ANALYSIS_V2, 'IFCB_tools'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_v2, 'feature_extraction'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_v2, 'feature_extraction', 'blob_extraction'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_v2, 'feature_extraction', 'biovolume'),
                                   os.path.join(PATH_TO_EASY_IFCB, 'helpers'),
                                   PATH_TO_DIPUM)
        features = self.matlab_engine.fastFeatureExtraction(self.path_to_bin, bin_name, minimal_feature_flag, self.matlab_parallel_flag, nargout=1)
        features = pd.DataFrame(np.array(features._data).reshape(features.size[::-1]).T,
                                columns=FTR_V2_COLUMN_NAMES)
        features = features.astype({'ImageId': 'uint32', 'Area': 'uint64', 'NumberBlobsInImage': 'uint16'})
        features.set_index('ImageId', inplace=True)
        return features

    def extractFeatures_v4(self, bin_name, minimal_feature_flag=False):
        """ Extract features based on code in Development/Heidi_explore/blobs_for_biovolume
            from branch features_v3 of ifcb-analysis """
        if self.matlab_engine is None:
            # Start Matlab engine and add IFCB_analysis
            self.matlab_engine = matlab.engine.start_matlab()

        self.matlab_engine.addpath(os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'IFCB_tools'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'feature_extraction'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'feature_extraction', 'blob_extraction'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'feature_extraction', 'biovolume'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'Development', 'Heidi_explore', 'blobs_for_biovolume'),
                                   os.path.join(PATH_TO_EASY_IFCB, 'helpers'),
                                   PATH_TO_DIPUM)
        self.matlab_engine.cd(os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'Development', 'Heidi_explore', 'blobs_for_biovolume'))
        features = self.matlab_engine.fastFeatureExtraction_v4(self.path_to_bin, bin_name, minimal_feature_flag, self.matlab_parallel_flag, nargout=1)
        features = pd.DataFrame(np.array(features._data).reshape(features.size[::-1]).T,
                                columns=FTR_V4_COLUMN_NAMES)
        features = features.astype({'ImageId': 'uint32', 'Area': 'uint64', 'NumberBlobsInImage': 'uint16'})
        features.set_index('ImageId', inplace=True)
        return features

    def initEcoTaxaClassification(self, path_to_ecotaxa_tsv, path_to_taxonomic_grouping_csv):
        """ Build a table with id, taxon, group, and status for each image extracted from EcoTaxa """
        # Read EcoTaxa file(s)
        if os.path.isfile(path_to_ecotaxa_tsv):
            self.classification_data = pd.read_csv(path_to_ecotaxa_tsv, header=0, sep='\t', engine='c',
                                                   usecols=['object_id', 'object_annotation_status', 'object_annotation_hierarchy'],
                                                   dtype={'object_id': str, 'object_annotation_status': 'category', 'object_annotation_hierarchy': 'category'})
        elif os.path.isdir(path_to_ecotaxa_tsv):
            list_tsv = glob.glob(os.path.join(path_to_ecotaxa_tsv, '**', '*.tsv'))
            # Read each tsv file
            data = [None] * len(list_tsv)
            for i, f in enumerate(tqdm(list_tsv)):
                data[i] = pd.read_csv(f, header=0, sep='\t', engine='c',
                                      usecols=['object_id', 'object_annotation_status', 'object_annotation_hierarchy'],
                                      dtype={'object_id': str, 'object_annotation_status': 'category',
                                             'object_annotation_hierarchy': 'category'})
            # Union Categories
            us = union_categoricals([d.object_annotation_status for d in data])
            uh = union_categoricals([d.object_annotation_hierarchy for d in data])
            for i in range(len(data)):
                data[i].object_annotation_status = pd.Categorical(data[i].object_annotation_status,
                                                                  categories=us.categories)
                data[i].object_annotation_hierarchy = pd.Categorical(data[i].object_annotation_hierarchy,
                                                                     categories=uh.categories)
            # Merge all files
            self.classification_data = pd.concat(data, ignore_index=True, axis=0)
        else:
            raise ValueError('EcoTaxa TSV file not found.')
        # Read taxonomic grouping
        taxonomic_grouping = pd.read_csv(path_to_taxonomic_grouping_csv, header=0, engine='c')

        # Quick reformating of EcoTaxa table
        self.classification_data.rename(columns={'object_id': 'id', 'object_annotation_status': 'AnnotationStatus',
                                                 'object_annotation_hierarchy': 'Hierarchy'},
                                        inplace=True)
        # Rename/Group categories
        taxon = pd.Series(taxonomic_grouping.taxon.values, index=taxonomic_grouping.hierarchy).to_dict()
        group = pd.Series(taxonomic_grouping.group.values, index=taxonomic_grouping.hierarchy).to_dict()
        self.classification_data['Taxon'] = self.classification_data.Hierarchy.apply(lambda x: taxon[x]).astype('category')
        self.classification_data['Group'] = self.classification_data.Hierarchy.apply(lambda x: group[x]).astype('category')
        # self.classification_data['Taxon'] = self.classification_data.Hierarchy.cat.rename_categories(taxon)  # Non unique new categories so does not work
        # self.classification_data['Group'] = self.classification_data.Hierarchy.cat.rename_categories(group)
        # Drop hierarchy
        self.classification_data.drop(columns={'Hierarchy'}, inplace=True)
        # Remove Incorrect ids
        sel = self.classification_data['id'].str.len() != 30
        if np.any(sel):
            sel = np.where(sel)[0]
            for i in sel:
                print('%s: Incorrect identification number from EcoTaxa' % self.classification_data['id'][i])
            self.classification_data.drop(index=sel, inplace=True)
        # Split EcoTaxa Id
        self.classification_data['bin'] = self.classification_data['id'].apply(lambda x: x[0:24]).astype('category')
        self.classification_data['ImageId'] = self.classification_data['id'].apply(lambda x: x[25:]).astype('uint32')

    def queryClassificationData(self, bin_name, verbose=True):
        """ query classification data previously loaded with initEcoTaxaClassification"""
        foo = self.classification_data[self.classification_data['bin'] == bin_name]
        if foo.empty:
            if verbose:
                print("%s: No classification data." % bin_name)
            return pd.DataFrame(columns=['AnnotationStatus', 'Taxon', 'Group'])
        else:
            # Check if all ImageId are unique
            if not foo.ImageId.is_unique:
                print("%s: Non unique classification for each image." % bin_name)
                foo = foo.sort_values('AnnotationStatus', ascending=False).drop_duplicates('ImageId')
            return foo.drop(columns=['id', 'bin']).set_index('ImageId')

    def queryEnvironmentalData(self, bin_name):
        foo = self.environmental_data[self.environmental_data['bin'].str.match(bin_name)]
        if foo.empty:
            raise ValueError('%s: No environmental data found.' % bin_name)
        elif len(foo.index) > 1:
            raise ValueError('%s: Non unique bin names in environmental data.' % bin_name)
        return foo.drop(columns={'bin'})

    def getBinData(self, bin_name, write_image=True, include_classification=True):
        # Extract cytometric data, features, clear environmental data, and classification for use in ecological studies
        cytometric_data = self.extractImagesAndCytometricData(bin_name, write_image=write_image)
        features = self.extractFeatures_v4(bin_name)
        if len(features.index) != len(cytometric_data):
            raise ValueError('%s: Cytometric and features data frames have different sizes.' % bin_name)
        if include_classification:
            if self.classification_data is None:
                raise ValueError("Classification data must be loaded first.")
            classification_data = self.queryClassificationData(bin_name, verbose=False)
            if len(classification_data.index) != len(cytometric_data):
                if classification_data.empty:
                    print('%s: No classification data.' % bin_name)
                else:
                    raise ValueError('Classification data incomplete: %d/%d' %
                          (len(classification_data.index), len(cytometric_data)))
            data = pd.concat([features, cytometric_data, classification_data], axis=1)
        else:
            data = pd.concat([features, cytometric_data], axis=1)
        return data

    def runForML(self, bin_name):
        """  Extract png, cytometric data, features, and obfuscated environmental data
         to classify oceanic plankton images with machine learning algorithms """
        # Write png and get cytometric data and features
        data = self.getBinData(bin_name, write_image=True, include_classification=False)
        # Get environmental data
        environmental_data = self.queryEnvironmentalData(bin_name)
        environmental_data = pd.DataFrame(np.repeat(environmental_data.values, len(data.index), axis=0),
                                          columns=environmental_data.columns)
        # Write data for machine learning
        data = pd.concat([data, environmental_data], axis=1)
        data.to_csv(os.path.join(self.path_to_output, bin_name, bin_name + '_ml.csv'),
                    index=False, na_rep='NaN', float_format='%.4f')

    def batchRunForML(self):
        """ Run runForML on list of bins loaded in environmental_data """
        for i in tqdm(range(len(ifcb.environmental_data.index))):
            try:
                if not os.path.isfile(os.path.join(self.path_to_bin, self.environmental_data['bin'][i] + '.roi')):
                    print('%s: missing roi file.' % self.environmental_data['bin'][i])
                    continue
                if os.path.exists(os.path.join(output_path, ifcb.environmental_data['bin'][i])):
                    print('%s: skipped' % self.environmental_data['bin'][i])
                    continue
                self.runForML(self.environmental_data['bin'][i])
            except:
                print('%s: Caught Error' % self.environmental_data['bin'][i])

    def runForEcoTaxa(self):
        # Extract png, cytometric data, features, instrument configuration, obfuscated environmental data, and classficiation for further validation with EcoTaxa
        # TODO prepare_bin_for_ecotaxa
        pass

    def runForScience(self, bin_list=None, update_all=False, update_classification=False):
        """ Generate a file per bin with cytometric data, features, and classification data
            Generate a metadata file with all environmental data and bin header information
            Intended for use in ecological studies """
        # Load previous metadata or create new one
        metadata_filename = os.path.join(self.path_to_output, 'metadata.csv')
        if os.path.isfile(metadata_filename):
            new_metadata_file = True
        else:
            new_metadata_file = False
        if new_metadata_file:
            metadata = pd.read_csv(metadata_filename)
            metadata.rename(columns={'BinId': 'bin'}, inplace=True)
        else:
            metadata = self.environmental_data
            for c in HDR_COLUMN_NAMES:
                metadata[c] = np.nan
            metadata['TriggerSelection'] = -9999
            metadata['AnnotationValidated'] = np.nan
        # Set list to parse
        if not bin_list:
            bin_list = metadata['bin']
        for bin_name in tqdm(bin_list):
            i = metadata.index[metadata['bin'] == bin_name]
            try:
                if not os.path.isfile(os.path.join(self.path_to_bin, bin_name + '.roi')):
                    print('%s: missing roi file.' % bin_name)
                    metadata.drop(index=i, inplace=True)
                    continue
                bin_filename = os.path.join(output_path, bin_name + '_sci.csv')
                if new_metadata_file or update_all or not os.path.isfile(bin_filename):
                    # Get header information
                    metadata.loc[i, HDR_COLUMN_NAMES] = self.extractBinHeader(bin_name).values[0]
                if not os.path.isfile(bin_filename) or update_all:
                    # Get cytometry, features, and classification and write to <bin_name>_sci.csv
                    data = self.getBinData(bin_name, write_image=False, include_classification=True)
                    data.to_csv(bin_filename,
                                na_rep='NaN', float_format='%.4f', index_label='ImageId')
                    # Get percent validated
                    if not data.empty:
                        metadata.loc[i, 'AnnotationValidated'] = np.sum(data['AnnotationStatus'] == 'validated') / len(
                            data.index)
                elif update_classification:
                    # Get classification data to get validation percentage for metadata file
                    data = self.queryClassificationData(bin_name, verbose=True)
                    if not data.empty:
                        foo = pd.read_csv(bin_filename, index_col='ImageId')
                        if foo.shape[0] != data.shape[0]:
                            print('%s: Unable to update classification, different sizes.' % bin_name)
                            continue
                        # Replace old columns by new ones
                        foo.drop(columns=data.columns, axis=0, inplace=True)
                        data = pd.concat([foo, data], axis=1)
                        data.to_csv(bin_filename,
                                    na_rep='NaN', float_format='%.4f', index_label='ImageId')
                        # Update percent validated in metadata
                        metadata.loc[i, 'AnnotationValidated'] = np.sum(data['AnnotationStatus'] == 'validated') / len(
                            data.index)
                elif new_metadata_file:
                    # Get classification data to get validation percentage for metadata file
                    data = self.queryClassificationData(bin_name, verbose=True)
                    if not data.empty:
                        # Get percent validated in metadata
                        metadata.loc[i, 'AnnotationValidated'] = np.sum(data['AnnotationStatus'] == 'validated') / len(
                            data.index)
                else:
                    # Bin already processed and does not need to be processed
                    # print('%s: skipped' % bin_name)
                    continue
            except Exception as e:
                print('%s: Caught Error: %s' % (bin_name, e))
        # Write metadata
        metadata['TriggerSelection'] = metadata['TriggerSelection'].astype('int64')
        metadata.rename(columns={'bin': 'BinId'}).to_csv(metadata_filename,
                        index=False, na_rep='NaN', float_format='%.4f')

    def checkMLData(self):
        flag = False
        # Get list of bins from 3 sources
        list_bins_env = list(self.environmental_data['bin'])
        list_bins_in = [b[0:-4] for b in os.listdir(self.path_to_bin) if b[-4:] == '.roi']
        list_bins_out = os.listdir(self.path_to_output)

        # Check no bins are missing
        if len(list_bins_env) != len(set(list_bins_env)):
            flag = True
            print('checkMLData: Non unique list of bins in environmental data')

        missing_bins_from_env = np.setdiff1d(list_bins_env, list_bins_out)
        if missing_bins_from_env.size > 0:
            flag = True
            print('checkMLData: Missing %d bins from environment file:' % missing_bins_from_env.size)
            for b in missing_bins_from_env:
                print('\t%s' % b)
            print()

        missing_bins_from_raw = np.setdiff1d(list_bins_in, list_bins_out)
        if missing_bins_from_raw.size > 0:
            flag = True
            print('checkMLData: Missing %d bins from raw folder:' % missing_bins_from_raw.size)
            for b in missing_bins_from_raw:
                print('\t%s' % b)
            print()

        # Check that each bin is complete
        n = 0;
        for b in tqdm(list_bins_out):
            path_to_metadata = os.path.join(self.path_to_output, b, b + '_ml.csv')
            if not os.path.exists(path_to_metadata):
                flag = True
                print('checkMLData: %s no metadata file.' % b)
                continue
            meta = pd.read_csv(path_to_metadata, header=0, engine='c')
            bin_name_parts = b.split('_')
            list_images_from_meta = ['%s%sP%05d.png' % (bin_name_parts[1], bin_name_parts[0], i) for i in meta['ImageId']]
            list_images_in_folder = [img for img in os.listdir(os.path.join(self.path_to_output, b)) if img[-4:] == '.png']

            missing_images_from_folder = np.setdiff1d(list_images_in_folder, list_images_from_meta)
            if missing_images_from_folder.size > 0:
                flag = True
                print('checkMLData: Missing %d images in %s:' % (missing_images_from_folder.size, b))
                for b in missing_images_from_folder:
                    print('\t%s' % b)
                print()

            missing_images_from_meta = np.setdiff1d(list_images_from_meta, list_images_in_folder)
            if missing_images_from_meta.size > 0:
                flag = True
                print('checkMLData: Missing %d metadata of %s:' % (missing_images_from_meta.size, b))
                for b in missing_images_from_meta:
                    print('\t%s' % b)
                print()

            n += len(list_images_in_folder)

        if not flag:
            print('checkMLData: Pass')

        print('%d images checked in %d bins' % (n,len(list_bins_out)))


if __name__ == '__main__':
    # Benchmark conversion from matlab to panda DataFrame
    # import timeit
    #     setup_features = '''
    # import numpy as np
    # import pandas as pd
    # import matlab.engine
    # matlab_engine = matlab.engine.start_matlab();
    # matlab_engine.addpath('/Users/nils/Documents/MATLAB/easyIFCB/IFCB_analysis/',
    #                       '/Users/nils/Documents/MATLAB/easyIFCB/IFCB_analysis/IFCB_tools',
    #                       '/Users/nils/Documents/MATLAB/easyIFCB/IFCB_analysis/feature_extraction',
    #                       '/Users/nils/Documents/MATLAB/easyIFCB/IFCB_analysis/feature_extraction/blob_extraction',
    #                       '/Users/nils/Documents/MATLAB/easyIFCB/IFCB_analysis/feature_extraction/biovolume',
    #                       '/Users/nils/Documents/MATLAB/easyIFCB/helpers',
    #                       '/Users/nils/Documents/MATLAB/easyIFCB/DIPUM/')
    # FTR_COLUMN_NAMES = ['ImageId', 'Area', 'NumberBlobsInImage',
    #                     'EquivalentDiameter', 'FeretDiameter', 'MinorAxisLength', 'MajorAxisLength', 'Perimeter', 'Biovolume',
    #                     'TextureContrast', 'TextureGrayLevel', 'TextureEntropy', 'TextureSmoothness', 'TextureUniformity']
    # features = matlab_engine.fastFeatureExtraction('/Users/nils/Data/NAAMES/NAAMES1/IFCB/raw/', 'D20151119T072930_IFCB107', nargout=1)
    # '''`
    # print(timeit.timeit('np.array(features)', setup=setup_features, number=1000))
    # print(timeit.timeit('np.array(features._data).reshape(features.size[::-1]).T', setup=setup_features, number=1000))
    # print(timeit.timeit('pd.DataFrame(np.array(features._data).reshape(features.size[::-1]).T, columns=FTR_COLUMN_NAMES)', setup=setup_features, number=1000))

    # Run BinExtractor.extractSampleHeader to get Volume Sample and instrument settings for each run
    # input_path = '/Users/nils/Data/EXPORTS/IFCB107/raw/'
    # output_path = '/Users/nils/Data/MachineLearning/EXPORTS_sci/'
    # # bin_name = 'D20151119T072930_IFCB107'
    # ifcb = BinExtractor(input_path, output_path)
    # hdr = pd.DataFrame()
    # list_bin = [b[0:-4] for b in os.listdir(ifcb.path_to_bin) if b[-4:] == '.roi']
    # for b in tqdm(list_bin):
    #     hdr = hdr.append(pd.concat([pd.DataFrame([b], columns=['SampleId']), ifcb.extractSampleHeader(b)], axis=1))
    # hdr.to_csv(os.path.join(ifcb.path_to_output, 'EXPORTS_SamplesHeader.csv'), index=False, na_rep='NaN', float_format='%.2f')

    # Run BinExtractor to build scientific dataset NAAMES
    # path_to_bin = '/Users/nils/Data/NAAMES/IFCB/Raw'
    # path_to_env_csv = '/Users/nils/Data/NAAMES/IFCB/Metadata/NAAMES_metadata_20191111.csv'
    # path_to_taxonomic_grouping_csv = '/Users/nils/Data/NAAMES/IFCB/Metadata/taxonomic_grouping_v5.csv'
    # path_to_ecotaxa_dir = '/Users/nils/Data/NAAMES/IFCB/EcoTaxaExports/EcoTaxa_20191108_183345'
    # output_path = '/Users/nils/Data/NAAMES/IFCB/Products'
    # # matlab_engine = matlab.engine.start_matlab()
    # # matlab_engine.parpool()
    # ifcb = BinExtractor(path_to_bin, output_path, path_to_env_csv, path_to_ecotaxa_dir, path_to_taxonomic_grouping_csv,
    #                     matlab_parallel_flag=True) # , matlab_engine=matlab_engine)
    # ifcb.runForScience()

    # Run BinExtractor to build scientific dataset EXPORTS
    # path_to_bin = '/Users/nils/Data/EXPORTS/IFCB107/raw'
    # path_to_env_csv = '/Users/nils/Data/EXPORTS/IFCB107/EXPORTS_metadata_20191113.csv'
    # path_to_taxonomic_grouping_csv = '/Users/nils/Data/NAAMES/IFCB/Metadata/taxonomic_grouping_v5.csv'
    # path_to_ecotaxa_dir = '/Users/nils/Data/EXPORTS/IFCB107/ecotaxa/EcoTaxa_20191115_091240'
    # output_path = '/Users/nils/Data/EXPORTS/IFCB107/SCI_20191115'
    # # bin_list_to_reprocess = ['D20180816T161819_IFCB107', 'D20180822T215513_IFCB107', 'D20180825T041958_IFCB107', 'D20180825T044222_IFCB107', 'D20180825T050445_IFCB107', 'D20180907T091008_IFCB107', 'D20180907T093232_IFCB107', 'D20180907T095456_IFCB107', 'D20180907T101719_IFCB107', 'D20180907T103943_IFCB107', 'D20180907T110207_IFCB107', 'D20180907T112430_IFCB107', 'D20180907T114654_IFCB107', 'D20180907T120918_IFCB107', 'D20180907T123141_IFCB107', 'D20180907T125405_IFCB107', 'D20180907T131629_IFCB107', 'D20180907T133853_IFCB107', 'D20180907T140116_IFCB107', 'D20180907T142340_IFCB107', 'D20180907T144604_IFCB107', 'D20180907T150827_IFCB107', 'D20180907T194131_IFCB107', 'D20180907T200354_IFCB107', 'D20180907T202618_IFCB107', 'D20180907T204842_IFCB107', 'D20180907T211105_IFCB107', 'D20180907T232243_IFCB107', 'D20180907T234507_IFCB107', 'D20180908T000731_IFCB107', 'D20180908T051444_IFCB107', 'D20180908T053707_IFCB107', 'D20180908T055931_IFCB107', 'D20180908T062155_IFCB107', 'D20180908T064418_IFCB107', 'D20180908T070642_IFCB107', 'D20180908T072905_IFCB107', 'D20180908T075129_IFCB107', 'D20180908T081352_IFCB107', 'D20180908T083616_IFCB107', 'D20180908T085840_IFCB107', 'D20180908T092103_IFCB107', 'D20180908T094327_IFCB107', 'D20180908T100550_IFCB107', 'D20180908T102814_IFCB107', 'D20180908T105038_IFCB107', 'D20180908T111301_IFCB107', 'D20180908T113525_IFCB107', 'D20180908T115748_IFCB107', 'D20180908T122012_IFCB107', 'D20180908T124235_IFCB107', 'D20180908T130459_IFCB107', 'D20180908T132723_IFCB107', 'D20180908T134946_IFCB107', 'D20180908T141210_IFCB107', 'D20180908T143433_IFCB107', 'D20180908T145657_IFCB107', 'D20180908T151920_IFCB107', 'D20180908T154144_IFCB107', 'D20180908T160408_IFCB107', 'D20180908T162631_IFCB107', 'D20180908T164855_IFCB107', 'D20180908T171118_IFCB107', 'D20180908T173342_IFCB107', 'D20180908T175605_IFCB107', 'D20180908T181829_IFCB107', 'D20180908T184053_IFCB107', 'D20180908T190316_IFCB107', 'D20180908T192540_IFCB107', 'D20180908T194803_IFCB107', 'D20180908T201027_IFCB107', 'D20180908T203251_IFCB107', 'D20180908T205514_IFCB107', 'D20180908T211738_IFCB107', 'D20180908T214001_IFCB107', 'D20180908T220225_IFCB107', 'D20180908T222448_IFCB107', 'D20180908T224712_IFCB107', 'D20180908T230935_IFCB107', 'D20180908T233159_IFCB107', 'D20180909T002302_IFCB107', 'D20180909T004526_IFCB107', 'D20180909T010750_IFCB107', 'D20180909T013013_IFCB107', 'D20180909T015237_IFCB107', 'D20180909T021500_IFCB107', 'D20180909T023724_IFCB107', 'D20180909T025947_IFCB107', 'D20180909T032211_IFCB107', 'D20180909T034435_IFCB107', 'D20180909T040658_IFCB107', 'D20180909T042922_IFCB107', 'D20180909T045145_IFCB107', 'D20180909T051409_IFCB107', 'D20180909T053633_IFCB107', 'D20180909T061143_IFCB107', 'D20180909T063407_IFCB107', 'D20180909T065630_IFCB107', 'D20180909T071854_IFCB107', 'D20180909T074118_IFCB107', 'D20180909T080341_IFCB107', 'D20180909T082605_IFCB107', 'D20180909T084828_IFCB107', 'D20180909T091052_IFCB107', 'D20180909T093316_IFCB107', 'D20180909T095539_IFCB107', 'D20180909T101803_IFCB107', 'D20180909T104027_IFCB107', 'D20180909T110250_IFCB107', 'D20180909T112514_IFCB107', 'D20180909T114738_IFCB107', 'D20180909T121002_IFCB107', 'D20180909T123225_IFCB107', 'D20180909T125449_IFCB107', 'D20180909T131713_IFCB107', 'D20180909T133937_IFCB107', 'D20180909T140200_IFCB107', 'D20180909T142424_IFCB107', 'D20180909T144648_IFCB107', 'D20180909T150911_IFCB107', 'D20180909T153135_IFCB107', 'D20180909T155359_IFCB107', 'D20180909T161622_IFCB107', 'D20180909T163846_IFCB107', 'D20180909T170109_IFCB107', 'D20180909T172333_IFCB107', 'D20180909T174557_IFCB107', 'D20180909T180820_IFCB107', 'D20180909T183044_IFCB107', 'D20180909T185308_IFCB107', 'D20180909T191531_IFCB107', 'D20180909T193755_IFCB107', 'D20180909T200019_IFCB107', 'D20180909T202242_IFCB107', 'D20180909T204506_IFCB107', 'D20180909T210729_IFCB107', 'D20180909T212953_IFCB107', 'D20180909T215217_IFCB107', 'D20180909T221440_IFCB107', 'D20180909T223704_IFCB107', 'D20180909T225928_IFCB107', 'D20180909T232151_IFCB107', 'D20180909T234415_IFCB107', 'D20180910T000638_IFCB107', 'D20180910T002902_IFCB107', 'D20180910T012005_IFCB107', 'D20180910T014229_IFCB107', 'D20180910T020452_IFCB107', 'D20180910T022716_IFCB107', 'D20180910T024940_IFCB107', 'D20180910T031203_IFCB107', 'D20180910T033427_IFCB107', 'D20180910T035650_IFCB107', 'D20180910T041914_IFCB107', 'D20180910T044138_IFCB107', 'D20180910T050401_IFCB107', 'D20180910T052625_IFCB107', 'D20180910T054849_IFCB107', 'D20180910T061112_IFCB107', 'D20180910T063336_IFCB107', 'D20180910T065559_IFCB107', 'D20180910T071823_IFCB107', 'D20180910T074046_IFCB107', 'D20180910T080310_IFCB107', 'D20180910T082533_IFCB107', 'D20180910T084757_IFCB107', 'D20180910T091020_IFCB107', 'D20180910T093244_IFCB107', 'D20180910T095507_IFCB107', 'D20180910T101731_IFCB107', 'D20180910T103954_IFCB107', 'D20180910T110218_IFCB107', 'D20180910T112441_IFCB107', 'D20180910T114705_IFCB107', 'D20180910T120928_IFCB107', 'D20180910T123152_IFCB107', 'D20180910T125415_IFCB107', 'D20180910T131639_IFCB107', 'D20180910T133902_IFCB107', 'D20180910T140126_IFCB107', 'D20180910T142350_IFCB107', 'D20180910T144613_IFCB107', 'D20180910T150837_IFCB107', 'D20180910T153101_IFCB107', 'D20180910T155324_IFCB107', 'D20180910T161548_IFCB107', 'D20180910T163811_IFCB107', 'D20180910T170035_IFCB107', 'D20180910T172258_IFCB107', 'D20180910T174522_IFCB107', 'D20180910T180745_IFCB107', 'D20180910T183009_IFCB107', 'D20180910T185233_IFCB107', 'D20180910T191456_IFCB107', 'D20180910T193720_IFCB107', 'D20180910T202823_IFCB107', 'D20180910T205046_IFCB107', 'D20180910T211310_IFCB107', 'D20180910T213534_IFCB107', 'D20180910T215757_IFCB107', 'D20180910T222021_IFCB107', 'D20180910T224245_IFCB107', 'D20180910T230508_IFCB107', 'D20180910T232732_IFCB107', 'D20180910T234955_IFCB107', 'D20180911T001219_IFCB107', 'D20180911T003443_IFCB107', 'D20180911T005706_IFCB107', 'D20180911T011930_IFCB107', 'D20180911T014154_IFCB107', 'D20180911T020417_IFCB107', 'D20180911T022641_IFCB107', 'D20180911T024904_IFCB107', 'D20180911T031128_IFCB107', 'D20180911T033351_IFCB107', 'D20180911T035615_IFCB107', 'D20180911T041839_IFCB107', 'D20180911T044103_IFCB107', 'D20180911T050327_IFCB107', 'D20180911T052551_IFCB107', 'D20180911T054814_IFCB107', 'D20180911T061038_IFCB107', 'D20180911T063302_IFCB107', 'D20180911T065525_IFCB107', 'D20180911T071749_IFCB107', 'D20180911T074013_IFCB107', 'D20180911T080236_IFCB107', 'D20180911T082500_IFCB107', 'D20180911T084723_IFCB107', 'D20180911T090947_IFCB107', 'D20180911T093211_IFCB107', 'D20180911T095434_IFCB107', 'D20180911T101658_IFCB107', 'D20180911T103921_IFCB107', 'D20180911T110145_IFCB107', 'D20180911T112409_IFCB107', 'D20180911T114632_IFCB107', 'D20180911T120856_IFCB107', 'D20180911T123120_IFCB107', 'D20180911T125343_IFCB107', 'D20180911T131607_IFCB107', 'D20180911T133831_IFCB107', 'D20180911T140054_IFCB107', 'D20180911T142318_IFCB107', 'D20180911T144542_IFCB107', 'D20180911T153645_IFCB107', 'D20180911T155909_IFCB107', 'D20180911T162133_IFCB107', 'D20180911T164357_IFCB107', 'D20180911T170620_IFCB107', 'D20180911T172844_IFCB107', 'D20180911T175108_IFCB107', 'D20180911T181331_IFCB107', 'D20180911T183555_IFCB107', 'D20180911T185818_IFCB107', 'D20180911T192042_IFCB107', 'D20180911T194306_IFCB107', 'D20180911T200531_IFCB107', 'D20180911T202750_IFCB107', 'D20180911T205015_IFCB107', 'D20180911T211241_IFCB107', 'D20180911T213501_IFCB107', 'D20180911T215722_IFCB107']
    # # matlab_engine = matlab.engine.start_matlab()
    # # matlab_engine.parpool()
    # ifcb = BinExtractor(path_to_bin, output_path, path_to_env_csv, path_to_ecotaxa_dir, path_to_taxonomic_grouping_csv,
    #                     matlab_parallel_flag=True)#, matlab_engine=matlab_engine)
    # ifcb.runForScience(update_classification=True)
    # # ifcb.runForScience(bin_list_to_reprocess, update_classification=True)

    # Run BinExtractor to build scientific dataset of NAAMES BEADS
    # path_to_bin = '/Users/nils/Data/NAAMES/IFCB/Calibration/beads'
    # path_to_env_csv = '/Users/nils/Data/NAAMES/IFCB/Calibration/NAAMES_BEADS_metadata.csv'
    # path_to_taxonomic_grouping_csv = '/Users/nils/Data/NAAMES/IFCB/Calibration/beads_taxonomic_grouping.csv'
    # path_to_ecotaxa_dir = '/Users/nils/Data/NAAMES/IFCB/EcoTaxaExports/IFCB_NAAMES_Beads/ecotaxa_export_782_20191122_1923.tsv'
    # output_path = '/Users/nils/Data/NAAMES/IFCB/Calibration/BEADS_SCI_20191122'
    # # bin_list_to_reprocess = ['D20180816T161819_IFCB107', 'D20180822T215513_IFCB107', 'D20180825T041958_IFCB107', 'D20180825T044222_IFCB107', 'D20180825T050445_IFCB107', 'D20180907T091008_IFCB107', 'D20180907T093232_IFCB107', 'D20180907T095456_IFCB107', 'D20180907T101719_IFCB107', 'D20180907T103943_IFCB107', 'D20180907T110207_IFCB107', 'D20180907T112430_IFCB107', 'D20180907T114654_IFCB107', 'D20180907T120918_IFCB107', 'D20180907T123141_IFCB107', 'D20180907T125405_IFCB107', 'D20180907T131629_IFCB107', 'D20180907T133853_IFCB107', 'D20180907T140116_IFCB107', 'D20180907T142340_IFCB107', 'D20180907T144604_IFCB107', 'D20180907T150827_IFCB107', 'D20180907T194131_IFCB107', 'D20180907T200354_IFCB107', 'D20180907T202618_IFCB107', 'D20180907T204842_IFCB107', 'D20180907T211105_IFCB107', 'D20180907T232243_IFCB107', 'D20180907T234507_IFCB107', 'D20180908T000731_IFCB107', 'D20180908T051444_IFCB107', 'D20180908T053707_IFCB107', 'D20180908T055931_IFCB107', 'D20180908T062155_IFCB107', 'D20180908T064418_IFCB107', 'D20180908T070642_IFCB107', 'D20180908T072905_IFCB107', 'D20180908T075129_IFCB107', 'D20180908T081352_IFCB107', 'D20180908T083616_IFCB107', 'D20180908T085840_IFCB107', 'D20180908T092103_IFCB107', 'D20180908T094327_IFCB107', 'D20180908T100550_IFCB107', 'D20180908T102814_IFCB107', 'D20180908T105038_IFCB107', 'D20180908T111301_IFCB107', 'D20180908T113525_IFCB107', 'D20180908T115748_IFCB107', 'D20180908T122012_IFCB107', 'D20180908T124235_IFCB107', 'D20180908T130459_IFCB107', 'D20180908T132723_IFCB107', 'D20180908T134946_IFCB107', 'D20180908T141210_IFCB107', 'D20180908T143433_IFCB107', 'D20180908T145657_IFCB107', 'D20180908T151920_IFCB107', 'D20180908T154144_IFCB107', 'D20180908T160408_IFCB107', 'D20180908T162631_IFCB107', 'D20180908T164855_IFCB107', 'D20180908T171118_IFCB107', 'D20180908T173342_IFCB107', 'D20180908T175605_IFCB107', 'D20180908T181829_IFCB107', 'D20180908T184053_IFCB107', 'D20180908T190316_IFCB107', 'D20180908T192540_IFCB107', 'D20180908T194803_IFCB107', 'D20180908T201027_IFCB107', 'D20180908T203251_IFCB107', 'D20180908T205514_IFCB107', 'D20180908T211738_IFCB107', 'D20180908T214001_IFCB107', 'D20180908T220225_IFCB107', 'D20180908T222448_IFCB107', 'D20180908T224712_IFCB107', 'D20180908T230935_IFCB107', 'D20180908T233159_IFCB107', 'D20180909T002302_IFCB107', 'D20180909T004526_IFCB107', 'D20180909T010750_IFCB107', 'D20180909T013013_IFCB107', 'D20180909T015237_IFCB107', 'D20180909T021500_IFCB107', 'D20180909T023724_IFCB107', 'D20180909T025947_IFCB107', 'D20180909T032211_IFCB107', 'D20180909T034435_IFCB107', 'D20180909T040658_IFCB107', 'D20180909T042922_IFCB107', 'D20180909T045145_IFCB107', 'D20180909T051409_IFCB107', 'D20180909T053633_IFCB107', 'D20180909T061143_IFCB107', 'D20180909T063407_IFCB107', 'D20180909T065630_IFCB107', 'D20180909T071854_IFCB107', 'D20180909T074118_IFCB107', 'D20180909T080341_IFCB107', 'D20180909T082605_IFCB107', 'D20180909T084828_IFCB107', 'D20180909T091052_IFCB107', 'D20180909T093316_IFCB107', 'D20180909T095539_IFCB107', 'D20180909T101803_IFCB107', 'D20180909T104027_IFCB107', 'D20180909T110250_IFCB107', 'D20180909T112514_IFCB107', 'D20180909T114738_IFCB107', 'D20180909T121002_IFCB107', 'D20180909T123225_IFCB107', 'D20180909T125449_IFCB107', 'D20180909T131713_IFCB107', 'D20180909T133937_IFCB107', 'D20180909T140200_IFCB107', 'D20180909T142424_IFCB107', 'D20180909T144648_IFCB107', 'D20180909T150911_IFCB107', 'D20180909T153135_IFCB107', 'D20180909T155359_IFCB107', 'D20180909T161622_IFCB107', 'D20180909T163846_IFCB107', 'D20180909T170109_IFCB107', 'D20180909T172333_IFCB107', 'D20180909T174557_IFCB107', 'D20180909T180820_IFCB107', 'D20180909T183044_IFCB107', 'D20180909T185308_IFCB107', 'D20180909T191531_IFCB107', 'D20180909T193755_IFCB107', 'D20180909T200019_IFCB107', 'D20180909T202242_IFCB107', 'D20180909T204506_IFCB107', 'D20180909T210729_IFCB107', 'D20180909T212953_IFCB107', 'D20180909T215217_IFCB107', 'D20180909T221440_IFCB107', 'D20180909T223704_IFCB107', 'D20180909T225928_IFCB107', 'D20180909T232151_IFCB107', 'D20180909T234415_IFCB107', 'D20180910T000638_IFCB107', 'D20180910T002902_IFCB107', 'D20180910T012005_IFCB107', 'D20180910T014229_IFCB107', 'D20180910T020452_IFCB107', 'D20180910T022716_IFCB107', 'D20180910T024940_IFCB107', 'D20180910T031203_IFCB107', 'D20180910T033427_IFCB107', 'D20180910T035650_IFCB107', 'D20180910T041914_IFCB107', 'D20180910T044138_IFCB107', 'D20180910T050401_IFCB107', 'D20180910T052625_IFCB107', 'D20180910T054849_IFCB107', 'D20180910T061112_IFCB107', 'D20180910T063336_IFCB107', 'D20180910T065559_IFCB107', 'D20180910T071823_IFCB107', 'D20180910T074046_IFCB107', 'D20180910T080310_IFCB107', 'D20180910T082533_IFCB107', 'D20180910T084757_IFCB107', 'D20180910T091020_IFCB107', 'D20180910T093244_IFCB107', 'D20180910T095507_IFCB107', 'D20180910T101731_IFCB107', 'D20180910T103954_IFCB107', 'D20180910T110218_IFCB107', 'D20180910T112441_IFCB107', 'D20180910T114705_IFCB107', 'D20180910T120928_IFCB107', 'D20180910T123152_IFCB107', 'D20180910T125415_IFCB107', 'D20180910T131639_IFCB107', 'D20180910T133902_IFCB107', 'D20180910T140126_IFCB107', 'D20180910T142350_IFCB107', 'D20180910T144613_IFCB107', 'D20180910T150837_IFCB107', 'D20180910T153101_IFCB107', 'D20180910T155324_IFCB107', 'D20180910T161548_IFCB107', 'D20180910T163811_IFCB107', 'D20180910T170035_IFCB107', 'D20180910T172258_IFCB107', 'D20180910T174522_IFCB107', 'D20180910T180745_IFCB107', 'D20180910T183009_IFCB107', 'D20180910T185233_IFCB107', 'D20180910T191456_IFCB107', 'D20180910T193720_IFCB107', 'D20180910T202823_IFCB107', 'D20180910T205046_IFCB107', 'D20180910T211310_IFCB107', 'D20180910T213534_IFCB107', 'D20180910T215757_IFCB107', 'D20180910T222021_IFCB107', 'D20180910T224245_IFCB107', 'D20180910T230508_IFCB107', 'D20180910T232732_IFCB107', 'D20180910T234955_IFCB107', 'D20180911T001219_IFCB107', 'D20180911T003443_IFCB107', 'D20180911T005706_IFCB107', 'D20180911T011930_IFCB107', 'D20180911T014154_IFCB107', 'D20180911T020417_IFCB107', 'D20180911T022641_IFCB107', 'D20180911T024904_IFCB107', 'D20180911T031128_IFCB107', 'D20180911T033351_IFCB107', 'D20180911T035615_IFCB107', 'D20180911T041839_IFCB107', 'D20180911T044103_IFCB107', 'D20180911T050327_IFCB107', 'D20180911T052551_IFCB107', 'D20180911T054814_IFCB107', 'D20180911T061038_IFCB107', 'D20180911T063302_IFCB107', 'D20180911T065525_IFCB107', 'D20180911T071749_IFCB107', 'D20180911T074013_IFCB107', 'D20180911T080236_IFCB107', 'D20180911T082500_IFCB107', 'D20180911T084723_IFCB107', 'D20180911T090947_IFCB107', 'D20180911T093211_IFCB107', 'D20180911T095434_IFCB107', 'D20180911T101658_IFCB107', 'D20180911T103921_IFCB107', 'D20180911T110145_IFCB107', 'D20180911T112409_IFCB107', 'D20180911T114632_IFCB107', 'D20180911T120856_IFCB107', 'D20180911T123120_IFCB107', 'D20180911T125343_IFCB107', 'D20180911T131607_IFCB107', 'D20180911T133831_IFCB107', 'D20180911T140054_IFCB107', 'D20180911T142318_IFCB107', 'D20180911T144542_IFCB107', 'D20180911T153645_IFCB107', 'D20180911T155909_IFCB107', 'D20180911T162133_IFCB107', 'D20180911T164357_IFCB107', 'D20180911T170620_IFCB107', 'D20180911T172844_IFCB107', 'D20180911T175108_IFCB107', 'D20180911T181331_IFCB107', 'D20180911T183555_IFCB107', 'D20180911T185818_IFCB107', 'D20180911T192042_IFCB107', 'D20180911T194306_IFCB107', 'D20180911T200531_IFCB107', 'D20180911T202750_IFCB107', 'D20180911T205015_IFCB107', 'D20180911T211241_IFCB107', 'D20180911T213501_IFCB107', 'D20180911T215722_IFCB107']
    # # matlab_engine = matlab.engine.start_matlab()
    # # matlab_engine.parpool()
    # ifcb = BinExtractor(path_to_bin, output_path, path_to_env_csv, path_to_ecotaxa_dir, path_to_taxonomic_grouping_csv,
    #                     matlab_parallel_flag=True)#, matlab_engine=matlab_engine)
    # ifcb.runForScience()

    # Run BinExtractor to build scientific dataset of BEADS April 2019
    path_to_bin = '/Users/nils/Data/IFCB_SizeCalibration/raw'
    path_to_env_csv = '/Users/nils/Data/IFCB_SizeCalibration/BEADS201904_metadata.csv'
    path_to_taxonomic_grouping_csv = '/Users/nils/Data/IFCB_SizeCalibration/beads_taxonomic_grouping.csv'
    path_to_ecotaxa_dir = '/Users/nils/Data/IFCB_SizeCalibration/ecotaxa/export/ecotaxa_export_2563_20191125_1920.tsv'
    output_path = '/Users/nils/Data/IFCB_SizeCalibration/BEADS201904_SCI_20191125'
    # bin_list_to_reprocess = ['D20180816T161819_IFCB107', 'D20180822T215513_IFCB107', 'D20180825T041958_IFCB107', 'D20180825T044222_IFCB107', 'D20180825T050445_IFCB107', 'D20180907T091008_IFCB107', 'D20180907T093232_IFCB107', 'D20180907T095456_IFCB107', 'D20180907T101719_IFCB107', 'D20180907T103943_IFCB107', 'D20180907T110207_IFCB107', 'D20180907T112430_IFCB107', 'D20180907T114654_IFCB107', 'D20180907T120918_IFCB107', 'D20180907T123141_IFCB107', 'D20180907T125405_IFCB107', 'D20180907T131629_IFCB107', 'D20180907T133853_IFCB107', 'D20180907T140116_IFCB107', 'D20180907T142340_IFCB107', 'D20180907T144604_IFCB107', 'D20180907T150827_IFCB107', 'D20180907T194131_IFCB107', 'D20180907T200354_IFCB107', 'D20180907T202618_IFCB107', 'D20180907T204842_IFCB107', 'D20180907T211105_IFCB107', 'D20180907T232243_IFCB107', 'D20180907T234507_IFCB107', 'D20180908T000731_IFCB107', 'D20180908T051444_IFCB107', 'D20180908T053707_IFCB107', 'D20180908T055931_IFCB107', 'D20180908T062155_IFCB107', 'D20180908T064418_IFCB107', 'D20180908T070642_IFCB107', 'D20180908T072905_IFCB107', 'D20180908T075129_IFCB107', 'D20180908T081352_IFCB107', 'D20180908T083616_IFCB107', 'D20180908T085840_IFCB107', 'D20180908T092103_IFCB107', 'D20180908T094327_IFCB107', 'D20180908T100550_IFCB107', 'D20180908T102814_IFCB107', 'D20180908T105038_IFCB107', 'D20180908T111301_IFCB107', 'D20180908T113525_IFCB107', 'D20180908T115748_IFCB107', 'D20180908T122012_IFCB107', 'D20180908T124235_IFCB107', 'D20180908T130459_IFCB107', 'D20180908T132723_IFCB107', 'D20180908T134946_IFCB107', 'D20180908T141210_IFCB107', 'D20180908T143433_IFCB107', 'D20180908T145657_IFCB107', 'D20180908T151920_IFCB107', 'D20180908T154144_IFCB107', 'D20180908T160408_IFCB107', 'D20180908T162631_IFCB107', 'D20180908T164855_IFCB107', 'D20180908T171118_IFCB107', 'D20180908T173342_IFCB107', 'D20180908T175605_IFCB107', 'D20180908T181829_IFCB107', 'D20180908T184053_IFCB107', 'D20180908T190316_IFCB107', 'D20180908T192540_IFCB107', 'D20180908T194803_IFCB107', 'D20180908T201027_IFCB107', 'D20180908T203251_IFCB107', 'D20180908T205514_IFCB107', 'D20180908T211738_IFCB107', 'D20180908T214001_IFCB107', 'D20180908T220225_IFCB107', 'D20180908T222448_IFCB107', 'D20180908T224712_IFCB107', 'D20180908T230935_IFCB107', 'D20180908T233159_IFCB107', 'D20180909T002302_IFCB107', 'D20180909T004526_IFCB107', 'D20180909T010750_IFCB107', 'D20180909T013013_IFCB107', 'D20180909T015237_IFCB107', 'D20180909T021500_IFCB107', 'D20180909T023724_IFCB107', 'D20180909T025947_IFCB107', 'D20180909T032211_IFCB107', 'D20180909T034435_IFCB107', 'D20180909T040658_IFCB107', 'D20180909T042922_IFCB107', 'D20180909T045145_IFCB107', 'D20180909T051409_IFCB107', 'D20180909T053633_IFCB107', 'D20180909T061143_IFCB107', 'D20180909T063407_IFCB107', 'D20180909T065630_IFCB107', 'D20180909T071854_IFCB107', 'D20180909T074118_IFCB107', 'D20180909T080341_IFCB107', 'D20180909T082605_IFCB107', 'D20180909T084828_IFCB107', 'D20180909T091052_IFCB107', 'D20180909T093316_IFCB107', 'D20180909T095539_IFCB107', 'D20180909T101803_IFCB107', 'D20180909T104027_IFCB107', 'D20180909T110250_IFCB107', 'D20180909T112514_IFCB107', 'D20180909T114738_IFCB107', 'D20180909T121002_IFCB107', 'D20180909T123225_IFCB107', 'D20180909T125449_IFCB107', 'D20180909T131713_IFCB107', 'D20180909T133937_IFCB107', 'D20180909T140200_IFCB107', 'D20180909T142424_IFCB107', 'D20180909T144648_IFCB107', 'D20180909T150911_IFCB107', 'D20180909T153135_IFCB107', 'D20180909T155359_IFCB107', 'D20180909T161622_IFCB107', 'D20180909T163846_IFCB107', 'D20180909T170109_IFCB107', 'D20180909T172333_IFCB107', 'D20180909T174557_IFCB107', 'D20180909T180820_IFCB107', 'D20180909T183044_IFCB107', 'D20180909T185308_IFCB107', 'D20180909T191531_IFCB107', 'D20180909T193755_IFCB107', 'D20180909T200019_IFCB107', 'D20180909T202242_IFCB107', 'D20180909T204506_IFCB107', 'D20180909T210729_IFCB107', 'D20180909T212953_IFCB107', 'D20180909T215217_IFCB107', 'D20180909T221440_IFCB107', 'D20180909T223704_IFCB107', 'D20180909T225928_IFCB107', 'D20180909T232151_IFCB107', 'D20180909T234415_IFCB107', 'D20180910T000638_IFCB107', 'D20180910T002902_IFCB107', 'D20180910T012005_IFCB107', 'D20180910T014229_IFCB107', 'D20180910T020452_IFCB107', 'D20180910T022716_IFCB107', 'D20180910T024940_IFCB107', 'D20180910T031203_IFCB107', 'D20180910T033427_IFCB107', 'D20180910T035650_IFCB107', 'D20180910T041914_IFCB107', 'D20180910T044138_IFCB107', 'D20180910T050401_IFCB107', 'D20180910T052625_IFCB107', 'D20180910T054849_IFCB107', 'D20180910T061112_IFCB107', 'D20180910T063336_IFCB107', 'D20180910T065559_IFCB107', 'D20180910T071823_IFCB107', 'D20180910T074046_IFCB107', 'D20180910T080310_IFCB107', 'D20180910T082533_IFCB107', 'D20180910T084757_IFCB107', 'D20180910T091020_IFCB107', 'D20180910T093244_IFCB107', 'D20180910T095507_IFCB107', 'D20180910T101731_IFCB107', 'D20180910T103954_IFCB107', 'D20180910T110218_IFCB107', 'D20180910T112441_IFCB107', 'D20180910T114705_IFCB107', 'D20180910T120928_IFCB107', 'D20180910T123152_IFCB107', 'D20180910T125415_IFCB107', 'D20180910T131639_IFCB107', 'D20180910T133902_IFCB107', 'D20180910T140126_IFCB107', 'D20180910T142350_IFCB107', 'D20180910T144613_IFCB107', 'D20180910T150837_IFCB107', 'D20180910T153101_IFCB107', 'D20180910T155324_IFCB107', 'D20180910T161548_IFCB107', 'D20180910T163811_IFCB107', 'D20180910T170035_IFCB107', 'D20180910T172258_IFCB107', 'D20180910T174522_IFCB107', 'D20180910T180745_IFCB107', 'D20180910T183009_IFCB107', 'D20180910T185233_IFCB107', 'D20180910T191456_IFCB107', 'D20180910T193720_IFCB107', 'D20180910T202823_IFCB107', 'D20180910T205046_IFCB107', 'D20180910T211310_IFCB107', 'D20180910T213534_IFCB107', 'D20180910T215757_IFCB107', 'D20180910T222021_IFCB107', 'D20180910T224245_IFCB107', 'D20180910T230508_IFCB107', 'D20180910T232732_IFCB107', 'D20180910T234955_IFCB107', 'D20180911T001219_IFCB107', 'D20180911T003443_IFCB107', 'D20180911T005706_IFCB107', 'D20180911T011930_IFCB107', 'D20180911T014154_IFCB107', 'D20180911T020417_IFCB107', 'D20180911T022641_IFCB107', 'D20180911T024904_IFCB107', 'D20180911T031128_IFCB107', 'D20180911T033351_IFCB107', 'D20180911T035615_IFCB107', 'D20180911T041839_IFCB107', 'D20180911T044103_IFCB107', 'D20180911T050327_IFCB107', 'D20180911T052551_IFCB107', 'D20180911T054814_IFCB107', 'D20180911T061038_IFCB107', 'D20180911T063302_IFCB107', 'D20180911T065525_IFCB107', 'D20180911T071749_IFCB107', 'D20180911T074013_IFCB107', 'D20180911T080236_IFCB107', 'D20180911T082500_IFCB107', 'D20180911T084723_IFCB107', 'D20180911T090947_IFCB107', 'D20180911T093211_IFCB107', 'D20180911T095434_IFCB107', 'D20180911T101658_IFCB107', 'D20180911T103921_IFCB107', 'D20180911T110145_IFCB107', 'D20180911T112409_IFCB107', 'D20180911T114632_IFCB107', 'D20180911T120856_IFCB107', 'D20180911T123120_IFCB107', 'D20180911T125343_IFCB107', 'D20180911T131607_IFCB107', 'D20180911T133831_IFCB107', 'D20180911T140054_IFCB107', 'D20180911T142318_IFCB107', 'D20180911T144542_IFCB107', 'D20180911T153645_IFCB107', 'D20180911T155909_IFCB107', 'D20180911T162133_IFCB107', 'D20180911T164357_IFCB107', 'D20180911T170620_IFCB107', 'D20180911T172844_IFCB107', 'D20180911T175108_IFCB107', 'D20180911T181331_IFCB107', 'D20180911T183555_IFCB107', 'D20180911T185818_IFCB107', 'D20180911T192042_IFCB107', 'D20180911T194306_IFCB107', 'D20180911T200531_IFCB107', 'D20180911T202750_IFCB107', 'D20180911T205015_IFCB107', 'D20180911T211241_IFCB107', 'D20180911T213501_IFCB107', 'D20180911T215722_IFCB107']
    # matlab_engine = matlab.engine.start_matlab()
    # matlab_engine.parpool()
    ifcb = BinExtractor(path_to_bin, output_path, path_to_env_csv, path_to_ecotaxa_dir, path_to_taxonomic_grouping_csv,
                        matlab_parallel_flag=True)  # , matlab_engine=matlab_engine)
    ifcb.runForScience()


    # Run BinExtractor for ML to classify dataset
    # input_path = '/Users/nils/Data/EXPORTS/IFCB107/raw/'
    # output_path = '/Users/nils/Data/MachineLearning/EXPORTS_ml/'
    # env_csv = '/Users/nils/Data/MachineLearning/KaggleDataset/EXPORTSEnvironmentalData_20190916.csv'
    # error: only one image in bin D20180907T150827_IFCB107
    # input_path = '/Users/nils/Data/PEACETIME/IFCB_107/raw/'
    # output_path = '/Users/nils/Data/MachineLearning/PEACETIME_ml/'
    # env_csv = '/Users/nils/Data/MachineLearning/KaggleDataset/PEACETIMEEnvironmentalData_20190916.csv'
    # input_path = '/Users/nils/Data/MachineLearning/NAAMES_raw/'
    # output_path = '/Users/nils/Data/MachineLearning/NAAMES_ml/'
    # env_csv = '/Users/nils/Data/MachineLearning/KaggleDataset/NAAMESEnvironmentalData_20190828.csv'
    # Start Matlab engine and parallel pool
    # matlab_engine = matlab.engine.start_matlab()
    # matlab_engine.parpool()
    # ifcb = BinExtractor(input_path, output_path, env_csv, matlab_engine=matlab_engine, atlab_parallel_flag=True)
    # ifcb.batchRunForML()
    # ifcb.checkMLData()
    # checkMLData: Missing 8 bins from raw folder:
    # D20170514T115029_IFCB107
    # D20170519T041154_IFCB107
    # D20170521T092311_IFCB107
    # D20170530T184341_IFCB107
    # D20170602T191959_IFCB107
    # D20170602T192641_IFCB107
    # D20170608T095453_IFCB107
    # D20170608T100037_IFCB107