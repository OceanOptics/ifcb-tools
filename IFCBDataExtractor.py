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
            print('Loading EcoTaxa TSV files')
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
                if len(classification_data.index) == 0:
                    print('%s: No classification data.' % bin_name)
                else:
                    print('%s: Classification data incomplete: %d/%d' %
                          (bin_name, len(classification_data.index), len(cytometric_data)))
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

    def runForScience(self):
        """ Generate a file per bin with cytometric data, features, and classification data
            Generate a metadata file with all environmental data and bin header information
            Intended for use in ecological studies """
        metadata = self.environmental_data
        for c in HDR_COLUMN_NAMES:
            metadata[c] = np.nan
        metadata['AnnotationValidated'] = np.nan
        for i in tqdm(metadata.index.to_list()):
            bin_name = metadata['bin'][i]  # 'D20151119T072930_IFCB107'
            try:
                if not os.path.isfile(os.path.join(self.path_to_bin, bin_name + '.roi')):
                    print('%s: missing roi file.' % bin_name)
                    metadata.drop(index=i, inplace=True)
                    continue
                # Get sample information
                metadata.loc[i, HDR_COLUMN_NAMES] = self.extractBinHeader(bin_name).values[0]
                if os.path.isfile(os.path.join(output_path, bin_name + '_sci.csv')):
                    # Skip getBinData as already processed
                    # print('%s: skipped' % bin_name)
                    # Get classification data to get validation percentage for metadata file
                    data = self.queryClassificationData(bin_name, verbose=True)
                else:
                    # Get data and write to <bin_name>_sci.csv
                    data = self.getBinData(bin_name, write_image=False, include_classification=True)
                    data.to_csv(os.path.join(self.path_to_output, bin_name + '_sci.csv'),
                                na_rep='NaN', float_format='%.4f', index_label='ImageId')
                # Get percent validated
                if len(data) > 0:
                    metadata.loc[i, 'AnnotationValidated'] = np.sum(data['AnnotationStatus'] == 'validated') / len(data.index)
            except Exception as e:
                print('%s: Caught Error: %s' % (bin_name, e))
        # Write metadata
        metadata.rename(columns={'bin': 'BinId'}).to_csv(os.path.join(self.path_to_output, 'metadata.csv'),
                        index=False, na_rep='NaN', float_format='%.4f')

    def exportToMatlab(self):
        """ Convert *_sci.csv files into matlab table """
        pass

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

    # Run BinExtractor to build scientific dataset
    path_to_bin = '/Users/nils/Data/NAAMES/IFCB/Raw'
    path_to_env_csv = '/Users/nils/Data/NAAMES/IFCB/Metadata/NAAMES_metadata_20191111.csv'
    path_to_taxonomic_grouping_csv = '/Users/nils/Data/NAAMES/IFCB/Metadata/taxonomic_grouping_v5.csv'
    path_to_ecotaxa_dir = '/Users/nils/Data/NAAMES/IFCB/EcoTaxaExports/EcoTaxa_20191108_183345'
    output_path = '/Users/nils/Data/NAAMES/IFCB/Products'
    # matlab_engine = matlab.engine.start_matlab()
    # matlab_engine.parpool()
    ifcb = BinExtractor(path_to_bin, output_path, path_to_env_csv, path_to_ecotaxa_dir, path_to_taxonomic_grouping_csv,
                        matlab_parallel_flag=True) # , matlab_engine=matlab_engine)
    ifcb.runForScience()
    # data = ifcb.getBinData('D20160515T231528_IFCB107', write_image=False)
    # data = ifcb.queryClassificationData('D20160518T222942_IFCB107')
    # data = ifcb.queryClassificationData('D20160521T060938_IFCB107')
    # ifcb.exportToMatlab()

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