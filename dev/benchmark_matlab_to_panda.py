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
