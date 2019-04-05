% Make a wonderful table of IFCB samples including:
%   + all NAAMES data
%   + calibrated features (pixel to um)
%   + reliable samples (flag and trigger selection)

cfg.path2data = '/Users/nils/Data/NAAMES/';

%% Load IFCB data
fprintf('Loading IFCB tables ... ');
in1 = load([cfg.path2data 'NAAMES1/IFCB/other/meta_hdr_ftr_adc.mat']); in1 = in1.ifcb;
in2 = load([cfg.path2data 'NAAMES2/IFCB/other/meta_hdr_ftr_adc.mat']); in2 = in2.ifcb;
in3 = load([cfg.path2data 'NAAMES3/IFCB/other/meta_hdr_ftr_adc.mat']); in3 = in3.ifcb;
in4 = load([cfg.path2data 'NAAMES4/IFCB/other/meta_hdr_ftr_adc.mat']); in4 = in4.ifcb;
fprintf('Done\n');
fprintf('Reformating IFCB tables ... ');
ifcb = [in1; in2; in3; in4];
ifcb.campaign_id = [ones(size(in1,1),1) * 1; ones(size(in2,1),1) * 2; ones(size(in3,1),1) * 3; ones(size(in4,1),1) * 4];
ifcb = movevars(ifcb,'campaign_id','Before','stn_id');
ifcb.type = categorical(ifcb.type);
fprintf('Done\n');

%% Load EcoTaxa data (in each campaign directory) DEPRECATED
% Used before code from Jason that automatically pull data from EcoTaxa
% date_export = '20190125';
% ifcb_ecotaxa_output_dir = {['NAAMES1/IFCB/ecotaxa_output/' date_export '/'], ['NAAMES2/IFCB/ecotaxa_output/' date_export '/'], ['NAAMES3/IFCB/ecotaxa_output/' date_export '/'], ['NAAMES4/IFCB/ecotaxa_output/' date_export '/']};
% d = table({},{},{},'VariableNames', {'object_id', 'object_annotation_hierarchy', 'object_annotation_status'});
% for i=1:4
%   l=dir([cfg.path2data ifcb_ecotaxa_output_dir{i} '*.tsv']);
%   for j=1:length(l)
%     fprintf('Reading %s ... ', l(j).name);
%     buffer = readtable([l(j).folder '/' l(j).name],'FileType','text', 'Delimiter', '\t');
%     d = [d; table(buffer.object_id, buffer.object_annotation_hierarchy, buffer.object_annotation_status,...
%                   'VariableNames', {'object_id', 'object_annotation_hierarchy', 'object_annotation_status'})];
%     fprintf('Done\n');
%   end
% end

%% Load EcoTaxa data
% Meant to be used with Jason's export utility
date_export = '190420';
data_version = '10'; % used for saving file only
% Get name of all dirs
ifcb_ecotaxa_output_dir = [cfg.path2data 'NAAMES*/IFCB/ecotaxa_output/*_' date_export '_*/*/*.tsv'];

d = table({},{},{},[], 'VariableNames', {'object_id', 'object_annotation_hierarchy', 'object_annotation_status', 'object_annotation_dt'});
l=dir(ifcb_ecotaxa_output_dir);
for j=1:length(l)
  fprintf('Reading %s ... ', l(j).name);
  buffer = readtable([l(j).folder '/' l(j).name],'FileType','text', 'Delimiter', '\t');
  % Format date (very slow, needed to plot cumulative annotation with time)
  buffer.object_annotation_dt = datenum(strcat(buffer.object_annotation_date, buffer.object_annotation_time), 'yyyymmddHHMMSS');
  buffer.object_annotation_dt(cellfun(@isempty, buffer.object_annotation_date)) = NaN;
%   buffer.object_annotation_dt = NaN; % can replace slow function above by this to run faster
  % Add to table
  d = [d; table(buffer.object_id, buffer.object_annotation_hierarchy, buffer.object_annotation_status,...
                buffer.object_annotation_dt,...
                'VariableNames', {'object_id', 'object_annotation_hierarchy', 'object_annotation_status', 'object_annotation_dt'})];
  fprintf('Done\n');
end

%% Plot Cumulative Distribution function
% Compute cumulative counts
dt = datenum(2017,01,01):today();
cc = zeros(size(dt));
list = d.object_annotation_dt;
% Init
sel = list < dt(1); cc(1) = sum(sel); list = list(~sel);
% Cumulative Counts
for i=2:length(dt)
  sel = list < dt(i);
  cc(i) = cc(i-1) + sum(sel);
  list = list(~sel);
end

%% Plot
fig(1); hold('on');
area(dt,cc, 'FaceAlpha', 0.5, 'FaceColor', lines(1), 'EdgeColor', lines(1));
xlim([dt(1) dt(end)]);
plot(xlim(), 10^5 * ones(2,1), 'k--');
plot(xlim(), 10^6 * ones(2,1), 'k--');
plot(xlim(), 2 * 10^6 * ones(2,1), 'k--');
ylabel('Ecotaxa Annotations (#)');
text(today(), cc(end), sprintf('%1.3f\\times10^{6}', cc(end)/10^6), 'HorizontalAlignment', 'right', 'VerticalAlignment', 'bottom', 'FontSize', 16);
datetick2_doy(); set(datacursormode(figure(1)),'UpdateFcn',@data_cursor_display_date);
title(['IFCB v' data_version ' - ' datestr(datenum('190420', 'yymmdd'), 'mmmm dd, yyyy')]);
set(gca,'FontSize', 16, 'FontName', 'Helvetica Neue');
save_fig([cfg.path2data 'paperBB/figures/ecotaxa_images_validated'], 1024, 720);

%% Merge IFCB metadata with EcoTaxa classification
% remove non standard object_id
sel2rm = cellfun(@(x) length(x) ~= 30, d.object_id);
if any(sel2rm)
  fprintf('Removing unknown object_id:\n');
  for i=find(sel2rm)
    fprintf('\t%s\n', d.object_id{i});
  end
  d(sel2rm,:) = [];
end

% convert annotation hierarchy to simple names
fprintf('Renaming species and grouping species ... ');
pretty_taxo = readtable([cfg.path2data  'paperBB/user_input/taxonomic_grouping_v2.xlsx']);
% add each sample to raw file
for i=1:height(pretty_taxo)
  sel = strcmp(d.object_annotation_hierarchy, pretty_taxo.hierarchy{i});
  if any(sel)
    d.species(sel) = {pretty_taxo.category_prettified{i}};
    d.groups(sel) = {pretty_taxo.category_grouped{i}};
  end
end
fprintf('Done\n');

% replace empty annotation status by not classified
fprintf('Looking for non-classified data ... ');
sel = cellfun(@isempty, d.object_annotation_status);
d.object_annotation_status(sel) = {'not classified'};
fprintf('Done\n');

% Check for missing categories
fprintf('Checking for missing categories ... ');
sel = find(cellfun(@isempty, d.species));
if ~isempty(sel)
  foo = unique({d.object_annotation_hierarchy{sel}});
  fprintf('\nMissing following hierarchy in pretty_taxo:\n');
  for f=foo
    fprintf('%s\n', f{1});
  end
  return
end
fprintf('Done\n');

% Categories for d 
fprintf('Optimizing d fields ... ');
d.species = categorical(d.species);
d.groups = categorical(d.groups);
d.object_annotation_status = categorical(d.object_annotation_status);
fprintf('Done\n');

% for each ifcb samples add species and group
fprintf('Adding EcoTaxa classification to ifcb table ... \n'); tic
ifcb.Species = cell(height(ifcb), 1);
ifcb.Groups = cell(height(ifcb), 1);
ifcb.AnnotationStatus = cell(height(ifcb), 1);
ifcb.AnnotationValidated = NaN(height(ifcb), 1);
d = sortrows(d,'object_id','ascend'); % sort rows of d to match order of ifcb.ROIid
% d.sample_id = cellfun(@(x) x(1:24), d.object_id, 'UniformOutput', false);
d.sample_id = categorical(cellfun(@(x) x(1:24), d.object_id, 'UniformOutput', false));
dispLastStep = 0;
for i=1:height(ifcb)
%   sel = strcmp(d.sample_id, ifcb.id{i});
  sel = d.sample_id == ifcb.id{i}; % Runs much faster using categories
  n = sum(sel);
  if n == size(ifcb.ROIid{i}, 1)
    ifcb.Species{i} = d.species(sel);
    ifcb.Groups{i} = d.groups(sel);
    ifcb.AnnotationStatus{i} = d.object_annotation_status(sel);
    % Get ratio of sample validated (1 -> all validated, 0 -> all predicted)
%     ifcb.AnnotationValidated(i) = sum(strcmp(d.object_annotation_status(sel), 'validated')) ./ n;
    ifcb.AnnotationValidated(i) = sum(d.object_annotation_status(sel) == 'validated') ./ n;
  elseif n > 0
    fprintf('%s: Inconsistent number of samples %d, %d\n',ifcb.id{i}, n, size(ifcb.ROIid{i}, 1));
  end
  % Display Progress (not available wih parfor
  if floor((i/height(ifcb)) * 100) == dispLastStep + 1
    dispLastStep = floor(i/height(ifcb) * 100);
    fprintf('%3d/100\t%s\n', dispLastStep,ifcb.id{i});
  end
end
fprintf('Done\n'); toc

% Optimize table storage (already done before)
% turn cell array of string into categories
% fprintf('Optimizing table storage ... ');
% for i=1:height(ifcb) %% Not usefull as there is alredy optimized in variable d at previous step
%   ifcb.Species{i} = categorical(ifcb.Species{i});
%   ifcb.Groups{i} = categorical(ifcb.Groups{i});
%   ifcb.AnnotationStatus{i} = categorical(ifcb.AnnotationStatus{i});
% end
% fprintf('Done\n');

%% Calibrate IFCB samples (pixels to um)
IFCB_RESOLUTION = 3.4;
fprintf('Calibrating ... ');
ifcb.Area = cellfun(@(x) x * 1/IFCB_RESOLUTION^2, ifcb.Area, 'UniformOutput', false);
ifcb.Biovolume = cellfun(@(x) x * 1/IFCB_RESOLUTION^3, ifcb.Biovolume, 'UniformOutput', false);
ifcb.ConvexArea = cellfun(@(x) x * 1/IFCB_RESOLUTION^2, ifcb.ConvexArea, 'UniformOutput', false);
ifcb.ConvexPerimeter = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.ConvexPerimeter, 'UniformOutput', false);
ifcb.FeretDiameter = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.FeretDiameter, 'UniformOutput', false);
ifcb.MajorAxisLength = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.MajorAxisLength, 'UniformOutput', false);
ifcb.MinorAxisLength = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.MinorAxisLength, 'UniformOutput', false);
ifcb.Perimeter = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.Perimeter, 'UniformOutput', false);
ifcb.ESDA = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.ESDA, 'UniformOutput', false);
ifcb.ESDV = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.ESDV, 'UniformOutput', false);
ifcb.PA = cellfun(@(x) x * IFCB_RESOLUTION, ifcb.PA, 'UniformOutput', false);
% Change units
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'Area')} = 'um^2';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'Biovolume')} = 'um^3';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'ConvexArea')} = 'um^2';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'ConvexPerimeter')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'FeretDiameter')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'MajorAxisLength')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'MinorAxisLength')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'Perimeter')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'ESDA')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'ESDV')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'PA')} = '1/um';
fprintf('Done\n');

%% Check missing ecotaxa samples from EcoTaxa
fprintf('Missing EcoTaxa samples in inline:\n');
n = 0; m = 0;
for i=find(ifcb.type == 'inline')'
  if isempty(ifcb.Species{i})
    fprintf('N%d\t%s\n', ifcb.campaign_id(i), ifcb.id{i})
    n = n + length(ifcb.ROIid{i});
    m = m + 1;
  end
end
if n == 0
  fprintf('NONE :)\n');
else
  fprintf('Number of images missing: %d\n', n);
  fprintf('Number of samples missing: %d\n', m);
end
fprintf('Missing EcoTaxa samples in niskin:\n');
n = 0; m = 0;
for i=find(ifcb.type == 'niskin')'
  if isempty(ifcb.Species{i})
    fprintf('N%d\t%s\n', ifcb.campaign_id(i), ifcb.id{i})
    n = n + length(ifcb.ROIid{i});
    m = m + 1;
  end
end
if n == 0
  fprintf('NONE :)\n');
else
  fprintf('Number of images missing: %d\n', n);
  fprintf('Number of samples missing: %d\n', m);
end

%% Check incomplete ecotaxa samples from EcoTaxa
fprintf('Incomplete EcoTaxa samples in inline:\n');
n = 0; m = 0;
for i=find(ifcb.type == 'inline')'
  if ~isempty(ifcb.Species{i}) && length(ifcb.Species{i}) ~= length(ifcb.ROIid{i})
    fprintf('N%d\t%s\t%d\t %d\n', ifcb.campaign_id(i), ifcb.id{i}, length(ifcb.Species{i}), length(ifcb.ROIid{i}))
    n = n + abs(length(ifcb.ROIid{i}) - length(ifcb.Species{i}));
    m = m + 1;
  end
end
if n == 0
  fprintf('NONE :)\n');
else
  fprintf('Number of missing images: %d\n', n);
  fprintf('Number of samples incomplete: %d\n', m);
end
fprintf('Incomplete EcoTaxa samples in niskin:\n');
n = 0; m = 0;
for i=find(ifcb.type == 'niskin')'
  if ~isempty(ifcb.Species{i}) && length(ifcb.Species{i}) ~= length(ifcb.ROIid{i})
    fprintf('N%d\t%s\t%d\t %d\n', ifcb.campaign_id(i), ifcb.id{i}, length(ifcb.Species{i}), length(ifcb.ROIid{i}))
    n = n + abs(length(ifcb.ROIid{i}) - length(ifcb.Species{i}));
    m = m + 1;
  end
end
if n == 0
  fprintf('NONE :)\n');
else
  fprintf('Number of missing images: %d\n', n);
  fprintf('Number of samples incomplete: %d\n', m);
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
flags = arrayfun(@(x) find(bitget(x, 1:11))-1, ifcb.flag, 'UniformOutput', false);
fail = cellfun(@(y) any(y == 1 | y == 2 | y == 3 | y == 5 | y == 7 | y == 8 | y == 10), flags);
ifcb(fail,:) = [];
fprintf('Done\n');

%% Remove negative volumes (bug in software)
sel = ifcb.VolumeSampled < 0 | 5.5 < ifcb.VolumeSampled;
% for i=find(sel); fprintf('%s\n', ifcb.id{i}); end
fprintf('Removing %d un-real volumes (#bug) ... ', sum(sel));
ifcb(sel, :) = [];
fprintf('Done\n');

%% Check concentration
fprintf('Removing concentrated samples ... ');
% Remove concentration different than 1
ifcb(ifcb.concentration ~= 1, :) = [];
% Remove concentration variable
ifcb = removevars(ifcb, {'concentration'});
fprintf('Done\n');

%% Check trigger
%     - 1 PMT A Side scattering
%     - 2 PMT B Fluorescence
%     - 3 PMT A & B
% ifcb(ifcb.PMTtriggerSelection ~= 2,:) = [];

%% Save incubations for Francoise
% ifcb_incubation = ifcb(ifcb.type == 'incubation', :);
% fprintf('Saving incubations ... '); % Same versionning as ifcb.mat
% save([cfg.path2data 'paperBB/data/ifcb_incubation_v7'], 'ifcb_incubation');%, '-v7.3');
% fprintf('Done\n');

%% Remove types of samples not studied
fprintf('Removing unused type of samples ... ');
% Remove type of samples
ifcb(ifcb.type == 'PIC', :) = [];
ifcb(ifcb.type == 'ali6000', :) = [];
ifcb(ifcb.type == 'dock', :) = [];
ifcb(ifcb.type == 'micro-layer', :) = [];
% Remove fields linked to these type of samples
% ifcb(strcmp(ifcb.type, 'incubation'),:) = [];
ifcb(ifcb.type == 'incubation', :) = [];
ifcb = removevars(ifcb, {'experiment_state', 'experiment_dilution', 'experiment_light_level', 'experiment_nutrients', 'experiment_bottle_id'});
fprintf('Done\n');

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
fprintf('Saving ... ');
% save([cfg.path2data 'paperBB/data/ifcb_v' data_version], 'ifcb');%, '-v7.3');
fprintf('Done\n');

%% Quick extraction to update online files
ifcb2 = ifcb(:,[1, 6, 9, 10, 11, 12, 40]);
ifcb2.n = cellfun(@length, ifcb.ROIid);
% writetable(ifcb2, [cfg.path2data 'paperBB/data/IFCB_NAAAMES_Samples_v' data_version '.csv']);