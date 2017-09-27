% Check exported data for EcoTaxa
%   Look for NaN, infinit, or >float32 values.
% author: Nils Haëntjens
% created: May 2, 2016

%% 0. Load configuration
cfg.filename = 'cfg/PEACETIME.cfg';
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
fprintf('Done\n');

%% 1. Parameters
% Feature to load
cfg.feature.import = true;

%% 2. Import/Load all features
if cfg.feature.import
  fprintf('Importing features... ');  tic;% ~2 min
  bins=dir([cfg.path.features 'D*_fea_v2.csv']);
  bins={bins(:).name}; n = size(bins,2);
  bin=cell(n,1); dt=NaN(n,1); ftr=cell(n,1);
  if cfg.process.parallel; parfor_arg = Inf;
  else; parfor_arg = 0; end
  parfor (i=1:n, parfor_arg)
    ftr{i} = dlmread([cfg.path.features bins{i}], ',', 1); % Skip header line
    dt(i) = datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
    bin{i} = bins{i}(1:24);
  end
  % Save (checking size of variable ftr)
  varinfo=whos('ftr');
  saveopt='';
  if varinfo.bytes >= 2^31
    saveopt='-v7.3';
  end
  save([cfg.path.wk 'features_all'], 'dt', 'ftr', 'bin', saveopt);
  fprintf('Done\n'); toc;
else
  fprintf('Loading features... ');
  load([cfg.path.wk 'features_all']);
  fprintf('Done\n');
end
clearvars('-except', 'cfg', 'bin', 'dt', 'ftr');

%% 3. Look for any suspec value in each bin
% 3.1 Look into all bins at once
flagged=false(size(ftr));
for i=1:size(ftr,1)
  f=ftr{i};
  if any(isnan(f))
    flagged(i)=true;
  elseif any(isinf(f))
    flagged(i)=true;
  elseif any(any(-1.7976931348623157e+308 > f | f > 1.7976931348623157e+308))
    flagged(i)=true;
  end
end
flagged_index = find(flagged);
% disp('Bin(s) with with issue(s):');
% disp(flagged_index);

if ~isempty(flagged_index)
% 3.2 Look inside suspect bins
flagged_bin_index=[]; flagged_object_index=[]; flagged_feature_index=[];
for k=flagged_index
  f=ftr{k};
  for i=1:size(f,1)    % row: object
    for j=1:size(f,2)  % column: feature
      if any(isnan(f(i,j))) ||...
         any(isinf(f(i,j))) || ...
         any(any(-1.7976931348623157e+308 > f(i,j) | f(i,j) > 1.7976931348623157e+308))
        flagged_bin_index(end+1,1) = k;
        flagged_object_index(end+1,1) = i;
        flagged_feature_index(end+1,1) = j;
      end
    end
  end
end

% 3.3 Display what we found
fprintf('\nObject(s) not respecting EcoTaxa specifications:\n');
for k=1:size(flagged_bin_index,1)
  fprintf('bin: %s\tobject: %05d\tfeature: %03d\tvalue: %f\n',...
    bin{flagged_bin_index(k)},...
    ftr{flagged_bin_index(k)}(flagged_object_index(k),1),...
    flagged_feature_index(k),...
    ftr{flagged_bin_index(k)}(flagged_object_index(k),flagged_feature_index(k)));
end
else
  fprintf('No suspect roi found\n');
end

% TODO Check NAN Lat and Lon
%      Remove those columns in that case
      
