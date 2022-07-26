function make_ifcb_table(info, cfg)
% Make a wonderful table of IFCB samples including:
%   + all NAAMES data
%   + calibrated features (pixel to um)
%   + reliable samples (flag and trigger selection)

%addpath helpers/ ../utils/ProgressBar/

%% Configuration
% NAAMES
%info.PROJECT_NAME = 'NAAMES';
%info.ECOTAXA_EXPORT_DATE = '20211031';
%info.IFCB_RESOLUTION = 2.7488;
%info.CALIBRATED = true;
%IGNORE_FLUSH_FLAG = false;  % true for cultures | false otherwise
%info.REMOVED_CONCENTRATED_SAMPLES = true;
%cfg.path_to_input_data = '/Users/nils/Data/NAAMES/IFCB/SCI_20191111/';
%cfg.path_to_output_table = '/Users/nils/Data/NAAMES/IFCB/';
% EXPORTS
%info.PROJECT_NAME = 'EXPORTS';
%info.ECOTAXA_EXPORT_DATE = '20191115';
%info.IFCB_RESOLUTION = 2.7488;
%info.CALIBRATED = true;
%%IGNORE_FLUSH_FLAG = false;  % true for cultures | false otherwise
%info.REMOVED_CONCENTRATED_SAMPLES = false;
%cfg.path_to_input_data = '/Users/nils/Data/EXPORTS/IFCB107/SCI_20191115/';
%cfg.path_to_output_table = '/Users/nils/Data/EXPORTS/IFCB107/';
% %% NAAMES BEADS
% info.PROJECT_NAME = 'NAAMES_BEADS';
% info.ECOTAXA_EXPORT_DATE = '20191122';
% info.IFCB_RESOLUTION = 1;
% info.CALIBRATED = false;
% IGNORE_FLUSH_FLAG = true;
% info.REMOVED_CONCENTRATED_SAMPLES = true;
% cfg.path_to_input_data = '/Users/nils/Data/NAAMES/IFCB/Calibration/BEADS_SCI_20191122';
% cfg.path_to_output_table = '/Users/nils/Data/NAAMES/IFCB/Calibration/';
% %% NAAMES BEADS
% info.PROJECT_NAME = 'BEADS201904';
% info.ECOTAXA_EXPORT_DATE = '20191125';
% info.IFCB_RESOLUTION = 1;
% info.CALIBRATED = false;
% IGNORE_FLUSH_FLAG = true;
% info.REMOVED_CONCENTRATED_SAMPLES = false;
% cfg.path_to_input_data = '/Users/nils/Data/IFCB_SizeCalibration/BEADS201904_SCI_20191125';
% cfg.path_to_output_table = '/Users/nils/Data/IFCB_SizeCalibration/';

%% Load IFCB data
ifcb = importSCI(cfg.path_to_input_data);

%% Calibrate IFCB samples (pixels to um)
if info.CALIBRATED
fprintf('Calibrating ... ');
% um
list = {'EquivalentDiameter','MinFeretDiameter','MaxFeretDiameter','MinorAxisLength','MajorAxisLength','Perimeter', 'ConvexPerimeter', 'RepresentativeWidth'};
for f=list; f = f{1};
  ifcb.(f) = cellfun(@(x) x * 1/info.IFCB_RESOLUTION, ifcb.(f), 'UniformOutput', false);
  ifcb.Properties.VariableUnits{f} = 'um';
end
% um^2
list = {'Area', 'ConvexArea','SurfaceArea'};
for f=list; f = f{1};
  ifcb.(f) = cellfun(@(x) x * 1/info.IFCB_RESOLUTION^2, ifcb.(f), 'UniformOutput', false);
  ifcb.Properties.VariableUnits{f} = 'um^2';
end
% um^3
list = {'Biovolume'};
for f=list; f = f{1};
  ifcb.(f) = cellfun(@(x) x * 1/info.IFCB_RESOLUTION^3, ifcb.(f), 'UniformOutput', false);
  ifcb.Properties.VariableUnits{f} = 'um^3';
end
% counts
list = {'NumberBlobsInImage', 'NumberImagesInTrigger'};
for f=list; ifcb.Properties.VariableUnits{f{1}} = 'counts'; end
% degrees
list = {'Orientation'};
for f=list; ifcb.Properties.VariableUnits{f{1}} = 'degrees'; end
% Volts
list = {'SSCIntegrated','FLIntegrated','SSCPeak','FLPeak'};
for f=list; ifcb.Properties.VariableUnits{f{1}} = 'volts'; end
% Time
ifcb.Properties.VariableUnits{'TimeOfFlight'} = '???';
% Pixels
list = {'ImageX','ImageY','ImageWidth','ImageHeight'};
for f=list; ifcb.Properties.VariableUnits{f{1}} = 'pixels'; end
% no units
list = {'ImageId','Eccentricity','Extent','Solidity','AnnotationStatus','Taxon','Group'};
for f=list;
    if ~ismember(f{1}, ifcb.Properties.VariableNames); continue; end
    ifcb.Properties.VariableUnits{f{1}} = 'no units';
end
fprintf('Done\n');
end

%% Check missing ecotaxa samples from EcoTaxa
fprintf('Missing EcoTaxa samples in inline:\n');
n = 0; m = 0; l = {};
for i=find(ifcb.Type == 'inline')'
  if isnan(ifcb.AnnotationValidated(i)) && ~isempty(ifcb.BinId{i})
    if ismember('Campaign', ifcb.Properties.VariableNames)
      fprintf('N%d\t%s\n', ifcb.Campaign(i), ifcb.BinId{i});
    else
      fprintf('%s\n', ifcb.BinId{i});
    end
    n = n + length(ifcb.ImageId{i});
    m = m + 1;
    l{end+1} = ifcb.BinId{i};
  end
end
if m == 0
  fprintf('NONE :)\n');
else
  fprintf('Number of images missing: %d\n', n);
  fprintf('Number of samples missing: %d\n', m);
  info.MISSING_INLINE_CLASSIFICATION_IMAGES = n;
  info.MISSING_INLINE_CLASSIFICATION_BINS = m;
  info.MISSING_INLINE_CLASSIFICATION = l;
end

fprintf('Missing EcoTaxa samples in niskin:\n');
n = 0; m = 0; l = {};
for i=find(ifcb.Type == 'niskin')'
  if isnan(ifcb.AnnotationValidated(i)) && ~isempty(ifcb.BinId{i})
    if ismember('Campaign', ifcb.Properties.VariableNames)
      fprintf('N%d\t%s\n', ifcb.Campaign(i), ifcb.BinId{i});
    else
      fprintf('%s\n', ifcb.BinId{i});
    end
    n = n + length(ifcb.ImageId{i});
    m = m + 1;
    l{end+1} = ifcb.BinId{i};
  end
end
if m == 0
  fprintf('NONE :)\n');
else
  fprintf('Number of images missing: %d\n', n);
  fprintf('Number of samples missing: %d\n', m);
  info.MISSING_NISKIN_CLASSIFICATION_IMAGES = n;
  info.MISSING_NISKIN_CLASSIFICATION_BINS = m;
  info.MISSING_NISKIN_CLASSIFICATION = l;
end

%% Check flags
%     - 2^0  Good
%     - 2^1  Aborted | Incomplete (quantification can be biased)
%     - 2^2  Bad | Ignore | Delete | Failed | Bubbles
%     - 2^3  Questionnable
%     - 2^4  customTrigger: Trigger mode different than PMTB
%     - 2^5  Flush
%     - 2^6  customVolume: Volume sampled different than 5 mL
%     - 2^7  badAlignment (can underestimate concentration)
%     - 2^8  badFocus (area of particles is affected)
%     - 2^9  timeOffset: time of IFCB is incorrect
%     - 2^10 Corrupted (good sample, bad file)
fprintf('Removing flagged data ... ');
flags = arrayfun(@(x) find(bitget(x, 1:11))-1, ifcb.Flag, 'UniformOutput', false);
%if IGNORE_FLUSH_FLAG
%  fail = cellfun(@(y) any(y == 1 | y == 2 | y == 3 | y == 7 | y == 8 | y == 10), flags);
%  ifcb(fail,:) = [];
%  info.FLAGS_TO_REMOVE = [1 2 3 7 8 10];
%else
fail = cellfun(@(y) any(y == 1 | y == 2 | y == 3 | y == 5 | y == 7 | y == 8 | y == 10), flags);
ifcb(fail,:) = [];
info.FLAGS_TO_REMOVE = [1 2 3 5 7 8 10];
%end
info.REMOVED_BINS_FLAGGED = ifcb.BinId(fail);
fprintf('Done\n');

%% Remove negative volumes (bug in software)
sel = ifcb.VolumeSampled < 0 | 5.5 < ifcb.VolumeSampled;
% for i=find(sel); fprintf('%s\n', ifcb.id{i}); end
fprintf('Removing %d un-real volumes (#bug) ... ', sum(sel));
ifcb(sel, :) = [];
info.REMOVED_NON_REALISTIC_SAMPLE_VOLUME = ifcb.BinId(sel);
fprintf('Done\n');

%% Remove samples with no images
sel = cellfun(@isempty, ifcb.ImageId);
fprintf('Removing %d empty samples (no images) ... ', sum(sel));
ifcb(sel, :) = [];
info.REMOVED_EMPTY_SAMPLES = ifcb.BinId(sel);
fprintf('Done\n');

%% Check concentration
if info.REMOVED_CONCENTRATED_SAMPLES
  sel = ifcb.Concentration ~= 1;
  fprintf('Removing %d concentrated samples ... ', sum(sel));
  % Remove concentration different than 1
  ifcb(sel, :) = [];
  % Remove concentration variable
  ifcb = removevars(ifcb, {'Concentration'});
  info.REMOVED_CONCENTRATED_SAMPLES = ifcb.BinId(sel);
  fprintf('Done\n');
end

%% Check trigger
%     - 1 PMT A Side scattering
%     - 2 PMT B Fluorescence
%     - 3 PMT A & B
% ifcb(ifcb.PMTtriggerSelection ~= 2,:) = [];

%% Save incubations for Francoise
% ifcb_incubation = ifcb(ifcb.Type == 'incubation', :);
% fprintf('Saving incubations ... '); % Same versionning as ifcb.mat
% save([cfg.path2data 'paperBB/data/ifcb_incubation_v7'], 'ifcb_incubation');%, '-v7.3');
% fprintf('Done\n');

%% Remove types of samples not studied
fprintf('Removing unused type of samples ... ');
% Remove type of samples
types_to_rm = {'PIC', 'ali6000', 'dock', 'micro-layer', 'incubation', 'karen', 'test', 'towfish', 'zootow', 'culture'}; %'inline', 'niskin'
for t=types_to_rm
  ifcb(ifcb.Type == t{1}, :) = [];
end
ifcb.Type = removecats(ifcb.Type);
info.REMOVED_TYPES = types_to_rm;
fprintf('Done\n');
fprintf('Types left:\n'); for t=categories(ifcb.Type)'; fprintf('\t- %s\n', t{1}); end

%% Save
% v4: Aug, 2018
%     + remove flagged sampled
%     + keep only PMT B samples (no PMT A & B)
% v5: Sept 9, 2018
%     + keep only samples not concentrated
% v6: Dec 5, 2018
%     + load classification from EcoTaxa for all NAAMES 
%           Classification stopped Nov 30, 2018
%     + Taxonomic name based on taxonomic_grouping_v1.xlsx from Dec 4, 2018
%     + removed customTrigger filter (there is now cells that triggered on scat)
%     + removed unused type of data (PIC, ali6000, dock, micro-layer, incubation)
%     + removed unused fields (experiments_*)
%     + switch to categories for ifcb.type, ifcb.Species{:}, ifcb.Groups{:}, ifcb.AnnotationStatus{:}
%            for more efficient storage
% v7: Jan 25, 2019
%     + Updated classification from EcoTaxa on Jan 25, 2019
%     + added species:
%         living>Eukaryota>Archaeplastida>Viridiplantae>Chlorophyta>Chlorophyceae>Chlamydomonadales>Dunaliella
%         living>Eukaryota>Excavata>Discoba>Euglenozoa>Euglenida>Euglenales>Euglena
%         living>Eukaryota>Harosa>Alveolata>Myzozoa>Holodinophyta>Dinophyceae>Gymnodiniales>62>Gymnodiniaceae>Amphidinium
%         living>Eukaryota>Harosa>Alveolata>Myzozoa>Holodinophyta>Dinophyceae>Peridiniales>37>Peridiniaceae>Scrippsiella
%         living>Eukaryota>Harosa>Stramenopiles>Ochrophyta>Bacillariophyta>Bacillariophytina>Bacillariophyceae>Fragilaria
%         living>Eukaryota>Harosa>Stramenopiles>Ochrophyta>Bacillariophyta>Bacillariophytina>Mediophyceae>Thalassiosira>Thalassiosira weissflogii
%     + issues with samples:
%         D20151107T101753_IFCB107: Inconsistent number of samples 75, 76
%         D20160515T231528_IFCB107: Inconsistent number of samples 3382, 3566
%         D20160518T222942_IFCB107: Inconsistent number of samples 6089, 3045
%         D20160521T060938_IFCB107: Inconsistent number of samples 9506, 4862
%     + corrected NAAMES 3 sample metadata (inline->culture) D20170905T144021 
% v8: Mar 6, 2019
%     + Update EcoTaxa classification on March 6, 2019
% v9: Mar 20, 2019
%     + Update EcoTaxa classification on March 20, 2019
% v10: April 3, 2019
%     + Bug fix: incorrect units (stayed in pixels instead of being um after conversion)
%                does not affect values but just metadata
%     + Removed samples with negative volumes
% v11: April 25, 2019
%     + Automated pipeline from exporting all projects of EcoTaxa to making IFCB table
%     + No changes expected to the IFCB table
% v12-13: Exported by Jason Summer 2019
% v14: November 12, 2019
%     + extraction of data from raw files is done with python script IFCBDataExtractor.py
%     + updated to features_v4 from Heidi's code (improved blob extraction)

%info.TABLE_VERSION = 14;
info.CREATED = datestr(now(), 'yyyy/mm/dd HH:MM:SS');
fprintf('Saving MATLAB table ... ');
save([cfg.path_to_output_table filesep info.PROJECT_NAME '_IFCB_' info.ECOTAXA_EXPORT_DATE], 'ifcb', 'info');%, '-v7.3');
fprintf('Done\n');

end