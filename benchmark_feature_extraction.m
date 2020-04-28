
% small file to bench mark on
path_to_bin = '/Users/nils/Data/NAAMES/IFCB/Raw';
bin_name = 'D20151119T072930_IFCB107';
path_to_wk = '/Users/nils/Documents/MATLAB/easyIFCB/tmp';

% Tricky file to handle
path_to_bin ='/Users/nils/Data/EXPORTS/IFCB107/raw'
bin_name = 'D20180907T150827_IFCB107';

% Add path for v2
addpath(['IFCB_analysis/feature_extraction' filesep],...
        ['IFCB_analysis/feature_extraction' filesep 'blob_extraction' filesep],...
        ['IFCB_analysis/feature_extraction' filesep 'biovolume' filesep],...
        ['IFCB_analysis/IFCB_tools' filesep],...
        'helpers',...
        'DIPUM')

tic
f = fastFeatureExtraction_v2(path_to_bin, bin_name, false, true);
toc

restoredefaultpath
fprintf('Loading IFCB_analysis_v4... ');
addpath(['IFCB_analysis_v3/feature_extraction' filesep],...
        ['IFCB_analysis_v3/feature_extraction' filesep 'blob_extraction' filesep],...
        ['IFCB_analysis_v3/feature_extraction' filesep 'biovolume' filesep],...
        ['IFCB_analysis_v3/Development' filesep 'Heidi_explore' filesep 'blobs_for_biovolume' filesep],...
        ['IFCB_analysis_v3/IFCB_tools' filesep],...
        'helpers', 'DIPUM')
cd(['IFCB_analysis_v3/Development' filesep 'Heidi_explore' filesep 'blobs_for_biovolume' filesep]);
fprintf('Done\n');

tic
f = fastFeatureExtraction_v4(path_to_bin, bin_name, false, true);
toc
