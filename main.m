% IFCB to EcoTaxa
% Export IFCB raw data to png images and .tsv files compatible with EcoTaxa
%   Run the following steps:
%       1. Blob extraction
%       2. Feature analysis
%       3. Export PNG
%       4. Build TSV file
% author: Nils Haentjens <nils.haentjens+ifcb@maine.edu>
% created: May 21, 2016
% updated: July 12, 2016
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
if cfg.process.blobs;
  fprintf('Extracting '); tic;
  bins=dir([cfg.path.in 'D*.roi']);
  bins=regexprep({bins(:).name}', '.roi', '');
  dir_in=repmat(cellstr(cfg.path.in),size(bins,1),1);
  cfg.path.wk_blobs=[cfg.path.wk 'blobs'];
  dir_out=repmat(cellstr(cfg.path.wk_blobs),size(bins,1),1);
  fprintf('%d blobs... \n', size(bins,1));
  batch_blobs(dir_in, dir_out, bins, cfg.proc.parallel);
  %start_blob_batch_user_training(cfg.path.in, cfg.path.wk_blobs, cfg.proc.parallel);
  toc
  fprintf('Extraction of blobs done\n');
  clearvars('-except', 'cfg');
end;

%% 4. Features extraction
if cfg.process.features;
  fprintf('Extracting '); tic;
  bins=dir([cfg.path.in 'D*.roi']);
  bins=regexprep({bins(:).name}', '.roi', '');
  fprintf('%d features... \n', size(bins,1));
  dir_in_raw=repmat(cellstr(cfg.path.in),size(bins,1),1);
  cfg.path.wk_blobs=[cfg.path.wk 'blobs' filesep];
  dir_in_blob=repmat(cellstr(cfg.path.wk_blobs),size(bins,1),1);
  cfg.path.wk_features=[cfg.path.wk 'features' filesep];
  dir_out=cfg.path.wk_features;
  if ~isdir(dir_out); mkdir(dir_out); end;
  batch_features( dir_in_raw, bins, dir_out, dir_in_blob , cfg.proc.parallel);
  toc
  fprintf('Extraction of features done\n');
  clearvars('-except', 'cfg');
end;

%% 5. Images extraction
if cfg.process.images;
  fprintf('Extracting images...\n'); tic;
  cfg.path.wk_images=[cfg.path.wk 'images' filesep];
  dir_out=cfg.path.wk_images;
  % Loop through all the ROI files
  bins=dir([cfg.path.in 'D*.roi']);
  bins={bins(:).name};
%   if cfg.proc.parallel;
%     parfor b=bins;
%       bin_dir_out = [dir_out b{1}(1:end-4)];
%       if isdir(bin_dir_out);
%         fprintf('%s Skipping %s\n', utcdate(now()), b{1});
%       else
%         export_png_from_ROIlist([cfg.path.in b{1}(1:end-4)], bin_dir_out);
%         logmsg(['Extraction of ' b{1} ' Done']);
%       end;
%     end;
%   else
    for b=bins;
      bin_dir_out = [dir_out b{1}(1:end-4)];
      if isdir(bin_dir_out);
        fprintf('%s export_png SKIPPING %s\n', utcdate(now()), b{1});
      else
        fprintf('%s export_png EXTRACTING %s ... ', utcdate(now()), b{1});
        export_png_from_ROIlist([cfg.path.in b{1}(1:end-4)], bin_dir_out);
        fprintf('Done\n');
      end;
    end;
%   end;
  toc
  fprintf('Extraction of images done\n');
  clearvars('-except', 'cfg');
end;

%% 6. Export to EcoTaxa format
if cfg.process.export;
  fprintf('Exporting to EcoTaxa...\n'); tic;
  % ifcb2ecotaxa

  toc
  fprintf('Export to EcoTaxa done\n');
end;