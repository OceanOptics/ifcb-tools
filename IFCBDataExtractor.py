# Generate PNG and metadata from raw IFCB data and environmental data file

import pandas as pd
import numpy as np
import os
from PIL import Image
import matlab.engine
from tqdm import tqdm


ADC_COLUMN_NAMES = ['TriggerId', 'ADCTime', 'SSCIntegrated', 'FLIntegrated', 'PMTC', 'PMTD', 'SSCPeak', 'FLPeak', 'PeakC', 'PeakD',
                    'TimeOfFlight', 'GrabTimeStart', 'GrabTimeEnd', 'ImageX', 'ImageY', 'ImageWidth', 'ImageHeight', 'StartByte',
                    'ComparatorOut', 'StartPoint', 'SignalLength', 'Status', 'RunTime', 'InhibitTime']
ADC_COLUMN_SEL = ['SSCIntegrated', 'FLIntegrated', 'SSCPeak', 'FLPeak', 'TimeOfFlight',
                  'ImageX', 'ImageY', 'ImageWidth', 'ImageHeight', 'NumberImagesInTrigger']
FTR_COLUMN_NAMES = ['ImageId', 'Area', 'NumberBlobsInImage',
                    'EquivalentDiameter', 'FeretDiameter', 'MinorAxisLength', 'MajorAxisLength', 'Perimeter', 'Biovolume',
                    'TextureContrast', 'TextureGrayLevel', 'TextureEntropy', 'TextureSmoothness', 'TextureUniformity']
PATH_TO_IFCB_ANALYSIS = '/Users/nils/Documents/MATLAB/easyIFCB/IFCB_analysis/'
PATH_TO_DIPUM = '/Users/nils/Documents/MATLAB/easyIFCB/DIPUM/'
PATH_TO_EASY_IFCB = '/Users/nils/Documents/MATLAB/easyIFCB/'


class BinExtractor:

    path_to_bin = ''
    path_to_output = ''

    matlab_engine = None
    matlab_parallel_flag = False
    environmental_data = None

    def __init__(self, path_to_bin, path_to_output, path_to_environmental_csv, matlab_engine = None, matlab_parallel_flag=False):
        self.path_to_bin = path_to_bin
        self.path_to_output = path_to_output
        self.matlab_engine = matlab_engine
        self.matlab_parallel_flag = matlab_parallel_flag
        #   the environmental file must be in csv format and the first line must be the column names
        #   one of the column must be named "bin" and contain the bin id: D<yyyymmdd>T<HHMMSS>_IFCB<SN#>
        self.environmental_data = pd.read_csv(path_to_environmental_csv, header=0, engine='c')
        if 'bin' not in self.environmental_data:
            raise ValueError('Missing column bin in environmental data file.')

    def __del__(self):
        if self.matlab_engine is not None:
            self.matlab_engine.quit()

    def extractImagesAndCytometricData(self, bin_name):
        path_to_png = os.path.join(self.path_to_output, bin_name)
        # Parse ADC File
        adc = pd.read_csv(os.path.join(self.path_to_bin, bin_name + '.adc'), names=ADC_COLUMN_NAMES, engine='c',
                          na_values='-999.00000')
        adc['EndByte'] = adc['StartByte'] + adc['ImageWidth'] * adc['ImageHeight']
        # Get Number of ROI within one trigger
        adc['NumberImagesInTrigger'] = [sum(adc['TriggerId'] == x) for x in adc['TriggerId']]
        # Open ROI File
        roi = np.fromfile(os.path.join(self.path_to_bin, bin_name + '.roi'), 'uint8')
        bin_name_parts = bin_name.split('_')
        if not os.path.isdir(path_to_png):
            os.mkdir(path_to_png)
        rows_to_remove = list()
        for d in adc.itertuples():
            if d.StartByte != d.EndByte:
                # Save Image
                img = roi[d.StartByte:d.EndByte].reshape(d.ImageHeight, d.ImageWidth)
                # Save with ImageIO (slower)
                # imageio.imwrite(os.path.join(path_to_png, '%s%sP%05d.png' % (bin_name_parts[1], bin_name_parts[0], d.Index + 1)), img)
                # Save with PILLOW
                Image.fromarray(img).save(
                    os.path.join(path_to_png, '%s%sP%05d.png' % (bin_name_parts[1], bin_name_parts[0], d.Index + 1)),
                    'PNG')
            else:
                # Record lines to remove from adc
                rows_to_remove.append(d.Index)
        # Remove unused lines and columns from ADC
        adc = adc.drop(rows_to_remove)
        for k in adc.columns:
            if k not in ADC_COLUMN_SEL:
                del adc[k]
        return adc

    def extractFeatures(self, bin_name, minimal_feature_flag=False):
        if self.matlab_engine is None:
            # Start Matlab engine and add IFCB_analysis
            self.matlab_engine = matlab.engine.start_matlab()
            quit_matlab_engine = True

        self.matlab_engine.addpath(PATH_TO_IFCB_ANALYSIS,
                              os.path.join(PATH_TO_IFCB_ANALYSIS, 'IFCB_tools'),
                              os.path.join(PATH_TO_IFCB_ANALYSIS, 'feature_extraction'),
                              os.path.join(PATH_TO_IFCB_ANALYSIS, 'feature_extraction/blob_extraction'),
                              os.path.join(PATH_TO_IFCB_ANALYSIS, 'feature_extraction/biovolume'),
                              os.path.join(PATH_TO_EASY_IFCB, 'helpers'),
                              PATH_TO_DIPUM)
        features = self.matlab_engine.fastFeatureExtraction(self.path_to_bin, bin_name, minimal_feature_flag, self.matlab_parallel_flag, nargout=1)
        features = pd.DataFrame(np.array(features._data).reshape(features.size[::-1]).T,
                                columns=FTR_COLUMN_NAMES)
        # Not usefull as change as datatype change during concatenation
        # features = features.astype({'ImageId': 'uint32', 'Area': 'uint64', 'NumberBlobsInImage': 'uint8'})

        return features

    def extractInstrumentSettings(self, bin_name):
        pass

    def queryEnviromentalData(self, bin_name):
        foo = self.environmental_data[self.environmental_data['bin'].str.match(bin_name)]
        if foo.empty:
            raise ValueError('%s: No environmental data found.')
        elif len(foo.index) > 1:
            raise ValueError('%s: Non unique bin names in environmental data.' % bin_name)
        del foo['bin']
        return foo

    def runForML(self, bin_name):
        # Extract png, cytometric data, features, and obfuscated environmental data
        # to classify oceanic plankton images with machine learning algorithms
        cytometric_data = self.extractImagesAndCytometricData(bin_name)
        cytometric_data = cytometric_data.reset_index(drop=True)  # Reset index for merge with features table
        features = self.extractFeatures(bin_name)
        if len(features.index) != len(cytometric_data):
            raise ValueError('%s: Cytometric and features data frames have different sizes.' % bin_name)
        environmental_data = self.queryEnviromentalData(bin_name)
        environmental_data = pd.DataFrame(np.repeat(environmental_data.values, len(features.index), axis=0), columns=environmental_data.columns)
        meta = pd.concat([features, cytometric_data, environmental_data], axis=1)
        # Update data types
        meta = meta.astype({'ImageId': 'uint32', 'Area': 'uint64', 'NumberBlobsInImage': 'uint16', 'NumberImagesInTrigger': 'uint8'})
        # Write Metadata generated for machine learning
        meta.to_csv(os.path.join(self.path_to_output, bin_name, bin_name + '_ml.csv'), index=False, na_rep='NaN', float_format='%.4f')

    def runForEcoTaxa(self):
        # Extract png, cytometric data, features, instrument configuration, obfuscated environmental data, and classficiation for further validation with EcoTaxa
        # TODO prepare_bin_for_ecotaxa
        pass

    def runForScience(self):
        # Extract cytometric data, features, clear environmental data, and classification for use in ecological studies
        # TODO prepare_bin_for_science
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


    # Run BinExtractor for ML to classify dataset
    # # TODO Start Matlab engine and parpool before first iteration for improved tqdm estimation at the beigining
    input_path = '/Users/nils/Data/MachineLearning/NAAMES_raw/'
    output_path = '/Users/nils/Data/MachineLearning/NAAMES_ml/'
    ifcb = BinExtractor(input_path,
                        output_path,
                        '/Users/nils/Data/MachineLearning/KaggleDataset/NAAMESEnvironmentalData_20190828.csv',
                        matlab_parallel_flag=True)
    for i in tqdm(range(len(ifcb.environmental_data.index))):
        try:
            if not os.path.isfile(os.path.join(input_path, ifcb.environmental_data['bin'][i] + '.roi')):
                print('%s: missing roi file.' % ifcb.environmental_data['bin'][i])
                continue
            if os.path.exists(os.path.join(output_path, ifcb.environmental_data['bin'][i])):
                print('%s: skipped' % ifcb.environmental_data['bin'][i])
                continue
            ifcb.runForML(ifcb.environmental_data['bin'][i])
        except:
            print('%s: Caught Error' % ifcb.environmental_data['bin'][i])

    ifcb.checkMLData()
