% easyIFCB
% Export IFCB raw data to png images and .tsv files compatible with EcoTaxa
%   Run the following steps:
%       1. Blobs extraction
%       2. Features extraction
%       3. Images extraction
%       4. Build TSV file for ecotaxa
% author: Nils Haentjens <nils.haentjens+ifcb@maine.edu>
% created: May 21, 2016
% Acknowledge: Pierre-Luc Grandin and Heidi M. Sosik

clear();
close('all');
clc();

% Set location of configuration file
cfg.filename = 'default.cfg';

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%  No modifications needed below here  %%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% 1. Load configuration
fprintf('Loading configuration... ');

addpath('helpers');
cfg = loadCfg(cfg.filename);
fprintf('Done\n');

%% 2. Load IFCB_analysis code
fprintf('Loading IFCB_analysis... ');
addpath(cfg.path.ifcb_analysis,...
        [cfg.path.ifcb_analysis 'classification' filesep],...
        [cfg.path.ifcb_analysis 'classification' filesep 'batch_classification' filesep],...
        [cfg.path.ifcb_analysis 'feature_extraction' filesep],...
        [cfg.path.ifcb_analysis 'feature_extraction' filesep 'blob_extraction' filesep],...
        [cfg.path.ifcb_analysis 'feature_extraction' filesep 'batch_features_bins' filesep],...
        [cfg.path.ifcb_analysis 'feature_extraction' filesep 'biovolume' filesep],...
        [cfg.path.ifcb_analysis 'webservice_tools' filesep],...
        [cfg.path.ifcb_analysis 'IFCB_tools' filesep])
fprintf('Done\nLoading DIPUM... ');
addpath(cfg.path.dipum);
fprintf('Done\n');

%% 3. Blobs extraction
if cfg.process.blobs
  fprintf('Extracting blobs from '); tic;
  if strcmp(cfg.process.selection, 'all')
    bins=dir([cfg.path.in 'D*.roi']);
    bins={bins(:).name}';
  else
    f = fopen([cfg.path.selection cfg.process.selection]);
    bins = textscan(f, '%s'); bins = bins{1};
    fclose(f);
  end;
  bins=regexprep(bins, '.roi', '');
  dir_in=repmat(cellstr(cfg.path.in),size(bins,1),1);
  dir_out=repmat(cellstr(cfg.path.blobs),size(bins,1),1);
  fprintf('%d bin(s)... \n', size(bins,1));
  batch_blobs(dir_in, dir_out, bins, cfg.process.parallel);
  %start_blob_batch_user_training(cfg.path.in, cfg.path.wk_blobs, cfg.process.parallel);
  toc
  fprintf('Extraction of blobs done\n');
  clearvars('-except', 'cfg');
end;

%% 4. Features extraction
if cfg.process.features
  fprintf('Extracting features of '); tic;
  if strcmp(cfg.process.selection, 'all')
    bins=dir([cfg.path.in 'D*.roi']);
    bins={bins(:).name}';
  else
    f = fopen([cfg.path.selection cfg.process.selection]);
    bins = textscan(f, '%s'); bins = bins{1};
    fclose(f);
  end;
  bins=regexprep(bins, '.roi', '');
  fprintf('%d bin(s)... \n', size(bins,1));
  dir_in_raw=repmat(cellstr(cfg.path.in),size(bins,1),1);
  dir_in_blob=repmat(cellstr(cfg.path.blobs),size(bins,1),1);
  dir_out=cfg.path.features;
  if ~isdir(dir_out); mkdir(dir_out); end;
  batch_features( dir_in_raw, bins, dir_out, dir_in_blob , cfg.process.parallel);
  toc
  fprintf('Extraction of features done\n');
  clearvars('-except', 'cfg');
end;

%% 5. Run Classification
if cfg.process.classification
  fprintf('Classifying '); tic;
  if strcmp(cfg.process.selection, 'all')
    features = dir([cfg.path.features '*_fea_v2.csv']);
    features = {features(:).name}';
  else
    f = fopen([cfg.path.selection cfg.process.selection]);
    features = textscan(f, '%s'); features = features{1};
    features = cellfun(@(c)[c '_fea_v2.csv'],features,'uni',false);
    fclose(f);
  end;
  fprintf('%d bin(s)... \n', size(features,1));
  dir_out=cfg.path.classified;
  if ~isdir(dir_out); mkdir(dir_out); end;
  batch_classify( cfg.path.features, features, dir_out, cfg.path.classifier, cfg.process.parallel);
  toc
  fprintf('Extraction of features done\n');
  clearvars('-except', 'cfg');
end;

%% 6. Images extraction
if cfg.process.images
  fprintf('Extracting images...\n'); tic;
  dir_out=cfg.path.images;
  if strcmp(cfg.process.selection, 'all')
    bins=dir([cfg.path.in 'D*.roi']);
    bins={bins(:).name}';
  else
    f = fopen([cfg.path.selection cfg.process.selection]);
    bins = textscan(f, '%s'); bins = bins{1};
    fclose(f);
  end;
  bins=regexprep(bins, '.roi', '');
  
  scale_bar.pixel_per_micron = cfg.meta.scale_bar_pixel_per_micron;  % ratio
  scale_bar.height = cfg.meta.scale_bar_height;  % micron
  scale_bar.width = cfg.meta.scale_bar_width;  % micron
  % Parallel processing is not accelerating the process as it's mainly the
  % harddrive/SSD reading and writting.
  if cfg.process.parallel; parfor_arg = Inf;
  else; parfor_arg = 0; end;
  parfor (i=1:size(bins,1), parfor_arg)
%   for i=1:size(bins,1)
    bin_out = [dir_out bins{i}];
    if isdir(bin_out)
      fprintf('%s export_png SKIPPING %s\n', utcdate(now()), bins{i});
    else
      if cfg.process.parallel
        fprintf('%s export_png EXTRACTING %s ...\n', utcdate(now()), bins{i});
      else
        fprintf('%s export_png EXTRACTING %s ... ', utcdate(now()), bins{i});
      end;
      export2PNGWithScaleBar([cfg.path.in bins{i}], bin_out, [], scale_bar);
      if ~cfg.process.parallel; fprintf('DONE\n'); end;
    end;
  end;
  toc
  fprintf('Extraction of images done\n');
  clearvars('-except', 'cfg');
end;

%% 7. Export to EcoTaxa
if cfg.process.ecotaxa
  fprintf('Building EcoTaxa TSV files...\n'); tic;
  if strcmp(cfg.process.selection, 'all')
    features = dir([cfg.path.features '*_fea_v2.csv']);
    features = {features(:).name}';
    bins = cellfun(@(c)c(1:end-11) ,features,'uni',false);
  else
    f = fopen([cfg.path.selection cfg.process.selection]);
    bins = textscan(f, '%s'); bins = bins{1};
    features = cellfun(@(c)[c '_fea_v2.csv'],bins,'uni',false);
    fclose(f);
  end;
  fprintf('%d bin(s)... \n', size(features,1));
  dir_tsv=[cfg.path.ecotaxa 'tsv' filesep];
  if ~isdir(dir_tsv); mkdir(dir_tsv); end;
  buildEcoTaxaTSV( cfg.path.features, features, dir_tsv, cfg.path.meta, cfg, cfg.process.parallel);
  toc
  fprintf('Building EcoTaxa TSV files... done\n');
  fprintf('Consolidating EcoTaxa files...\n'); tic;
  dir_export=[cfg.path.ecotaxa 'import_' lower(cfg.process.selection_name) filesep];
  if ~isdir(dir_export); mkdir(dir_export); end;
  consolidateForEcoTaxa(cfg.path.images, dir_tsv, bins, dir_export, cfg.process.ecotaxa_zip, cfg.process.ecotaxa_rm_tmp, cfg.process.parallel);
  fprintf('Consolidating EcoTaxa files... done\n');
  toc
end;