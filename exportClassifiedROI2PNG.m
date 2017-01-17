% Export Classified Images in folders of each category
%   Classification must be run before
% author: Nils Haentjens
% created: July 21, 2016

%% 0. Load configuration
cfg.filename = 'default.cfg';
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
addpath([cfg.path.ifcb_analysis 'IFCB_tools' filesep],...
        [cfg.path.ifcb_analysis 'feature_extraction' filesep]);
fprintf('Done\n');

%% 1. Parameters
cfg.class.import = true;
cfg.path.wk_selection = [cfg.path.selection cfg.process.selection];

%% 2. Import/Load Classes
if cfg.class.import
  fprintf('Importing classes... ');  tic;% ~2 min
  bins=dir([cfg.path.classified 'D*_class_v1.mat']);
  bins={bins(:).name}; n = size(bins,2);
  % Load class names
  foo = load([cfg.path.classified bins{1}]);
  class_names = foo.class2useTB;
  % Load all data
  bin=cell(n,1); dt=NaN(n,1);
  roi_id=cell(n,1); TBclass=cell(n,1); TBclassQC=cell(n,1);
  if cfg.proc.parallel
    parfor i=1:n
      bin{i} = bins{i}(1:24);
      dt(i) = datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
      foo = load([cfg.path.classified bins{i}]);
      roi_id{i} = foo.roinum;
      TBclass{i} = cellfun(@(x) find(strcmp(class_names, x)), foo.TBclass);
      TBclassQC{i} = cellfun(@(x) find(strcmp(class_names, x)), foo.TBclass_above_threshold); 
    end;
  else
    for i=1:n
      bin{i} = bins{i}(1:24);
      dt(i) = datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
      foo = load([cfg.path.classified bins{i}]);
      roi_id{i} = foo.roinum;
      TBclass{i} = cellfun(@(x) find(strcmp(class_names, x)), foo.TBclass);
      TBclassQC{i} = cellfun(@(x) find(strcmp(class_names, x)), foo.TBclass_above_threshold); 
    end;
  end;
  save([cfg.path.wk 'classified'], 'bin', 'dt', 'roi_id', 'TBclass', 'TBclassQC', 'class_names');
  fprintf('Done\n'); toc;  
else
  fprintf('Loading classes... ');
  load([cfg.path.wk 'classified']);
  fprintf('Done\n');
end;
clearvars('-except', 'cfg', 'bin', 'dt', 'roi_id', 'TBclass', 'TBclassQC', 'class_names');

%% 3. Get selection
fprintf('Filtering data... ');
sel = getSelection(bin, cfg.path.wk_selection);
bin_sel = []; roi_id_sel = []; TBclass_sel=[]; TBclassQC_sel=[];
for i=sel'
  bin_sel(end + 1:end + size(roi_id{i},1),1) = i;
  roi_id_sel(end + 1:end + size(roi_id{i},1),1) = roi_id{i};
%   TBclass_sel(end + 1:end + size(TBclass{i},1),1) = TBclass{i};
  TBclassQC_sel(end + 1:end + size(TBclassQC{i},1),1) = TBclassQC{i};
end;
fprintf('Done\n');

%% 4. Export images
% This loop can be very long and generate a lot of data
fprintf('Exporting roi by class... \n');
dir_out = [cfg.path.wk 'images_' cfg.process.selection filesep];
if ~isdir(dir_out); mkdir(dir_out); end;  j = 1;
for i = 1:size(roi_id_sel,1)
  if i == 1 || bin_sel(i-1) ~= bin_sel(i)
    fprintf('%s export_png %d/%d EXTRACTING %s\n', utcdate(now()), j, size(sel,1), bin{bin_sel(i)});
    j = j + 1;
  end;
  % Set folder for class of roi
  img_dir = [dir_out class_names{TBclassQC_sel(i)}];
  if ~isdir(img_dir); mkdir(img_dir); end;
  % Export image to that location
  export_png_from_ROIlist([cfg.path.in bin{bin_sel(i)}], img_dir, roi_id_sel(i));
end;
fprintf('Exportation roi by class done\n');