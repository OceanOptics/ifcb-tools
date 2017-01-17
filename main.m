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
  fprintf('%d bins... \n', size(bins,1));
  batch_blobs(dir_in, dir_out, bins, cfg.proc.parallel);
  %start_blob_batch_user_training(cfg.path.in, cfg.path.wk_blobs, cfg.proc.parallel);
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
  fprintf('%d bins... \n', size(bins,1));
  dir_in_raw=repmat(cellstr(cfg.path.in),size(bins,1),1);
  dir_in_blob=repmat(cellstr(cfg.path.blobs),size(bins,1),1);
  dir_out=cfg.path.features;
  if ~isdir(dir_out); mkdir(dir_out); end;
  batch_features( dir_in_raw, bins, dir_out, dir_in_blob , cfg.proc.parallel);
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
  fprintf('%d bin of images... \n', size(features,1));
  dir_out=cfg.path.classified;
  if ~isdir(dir_out); mkdir(dir_out); end;
  batch_classify( cfg.path.features, features, dir_out, cfg.path.classifier, cfg.proc.parallel);
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
  % Parallel processing is not accelerating the process as it's mainly the
  % harddrive reading and writting.
%   if cfg.proc.parallel;
%     parfor b=bins;
%       bin_dir_out = [dir_out b{1}];
%       if isdir(bin_dir_out);
%         fprintf('%s export_png SKIPPING %s\n', utcdate(now()), b{1});
%       else
%         export_png_from_ROIlist([cfg.path.in b{1}], bin_dir_out);
%         logmsg(['EXTRACTION ' b{1} ' DONE']);
%       end;
%     end;
%   else
    for b=bins'
      bin_out = [dir_out b{1}];
      if isdir(bin_out)
        fprintf('%s export_png SKIPPING %s\n', utcdate(now()), b{1});
      else
        fprintf('%s export_png EXTRACTING %s ... ', utcdate(now()), b{1});
        export_png_from_ROIlist([cfg.path.in b{1}], bin_out);
        fprintf('DONE\n');
      end;
    end;
%   end;
  toc
  fprintf('Extraction of images done\n');
  clearvars('-except', 'cfg');
end;

%% 7. Export to EcoTaxa
if cfg.process.export
  fprintf('Exporting to EcoTaxa...\n'); tic;
  % ifcb2ecotaxa

  toc
  fprintf('Export to EcoTaxa done\n');
end;