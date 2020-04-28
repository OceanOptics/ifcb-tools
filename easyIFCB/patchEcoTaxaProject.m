%% ExoTaxa Project Patcher
% Patch ecotaxa ready files with updated tsv files
% author: nils
% created: Sept 28, 2017

clc
% 0. Parameters
% NAAMES
cruise='03';
cfg.filename = ['cfg/NAAMES' cruise '.cfg'];
% List of EcoTaxa Project to patch
cfg_ecotaxa_projects = {'import_inline_transit'};

% 1. Load configuration
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
addpath([cfg.path.ifcb_analysis 'feature_extraction' filesep])
fprintf('Done\n');
% List of patch
cfg_dir_patch = [cfg.path.ecotaxa 'tsv/'];


% 2. Get list of all bins in each project
for i=1:size(cfg_ecotaxa_projects,2)
  bin_to_patch{i} = dir([cfg.path.ecotaxa cfg_ecotaxa_projects{i} filesep 'D*']);
end

% 3. Loop through each new tsv and try to move it into a project
l = dir([cfg_dir_patch '*.tsv']);
for i=1:size(l,1)
  bin = l(i).name(9:end-4);
  patched = false;
  for j=1:size(cfg_ecotaxa_projects,2)
    foo = find(not(cellfun('isempty', strfind({bin_to_patch{j}.name}, bin))));
    if ~isempty(foo)
      fprintf('PATCHING %s ... \n', bin);
      movefile([l(i).folder filesep l(i).name], [bin_to_patch{j}(foo).folder filesep bin_to_patch{j}(foo).name])
      patched = true;
      continue
    end
  end
  if ~patched; fprintf('UNABLE TO PATCH %s\n', bin); end
end

