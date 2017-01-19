% Class distribution
%   Classification must be run before
%   Nicer pie chart can be viewed openning d3pie.html
% author: Nils Haentjens <nils.haentjens+ifcb@maine.edu>
% created: July 20, 2016

%% 0. Load configuration
cfg.filename = 'default.cfg';
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
fprintf('Done\n');

%% 1. Parameters
cfg.class.import = true;
cfg.class.name.update = true;
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
  if cfg.process.parallel; parfor_arg = Inf;
  else; parfor_arg = 0; end;
  parfor (i=1:n, parfor_arg)
    bin{i} = bins{i}(1:24);
    dt(i) = datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
    foo = load([cfg.path.classified bins{i}]);
    roi_id{i} = foo.roinum;
    TBclass{i} = cellfun(@(x) find(strcmp(class_names, x)), foo.TBclass);
    TBclassQC{i} = cellfun(@(x) find(strcmp(class_names, x)), foo.TBclass_above_threshold); 
  end;
  save([cfg.path.wk 'classes'], 'bin', 'dt', 'roi_id', 'TBclass', 'TBclassQC', 'class_names');
  fprintf('Done\n'); toc;  
else
  fprintf('Loading classes... ');
  load([cfg.path.wk 'classes']);
  fprintf('Done\n');
end;
clearvars('-except', 'cfg', 'bin', 'dt', 'TBclass', 'TBclassQC', 'class_names');
% Update names of class for labels in plot
if cfg.class.name.update
  for i=1:size(class_names,1)
    f = strfind(class_names{i}, '_');
    for j=1:size(f,2)
      class_names{i} = [class_names{i}(1:f(j)) '{' class_names{i}(f(j)+1:end) '}'];
    end;
  end;
end;

%% 3. Selection of data
sel = getSelection(bin, cfg.path.wk_selection);
TBclass_sel=[]; TBclassQC_sel=[];
for i=sel'
  TBclass_sel(end + 1:end + size(TBclass{i},1),1) = TBclass{i};
  TBclassQC_sel(end + 1:end + size(TBclassQC{i},1),1) = TBclassQC{i};
end;

%% 4. Compute distribution by class
n = size(TBclass_sel,1);
% Count
count = zeros(size(class_names));
countQC = count;
for i=1:n
  count(TBclass_sel(i)) = count(TBclass_sel(i)) + 1;
  countQC(TBclassQC_sel(i)) = countQC(TBclassQC_sel(i)) + 1;
end;
% Normalize
X = count / n;
XQC = countQC / n;
XQC2 = countQC(1:end-1) / (n - countQC(end)); % remove unclassified
% Add % in label
for i = 1:size(class_names,1)
  X_class_names{i} = [class_names{i} ' (' sprintf('%3.2f',X(i)*100) ' %)'];
  XQC_class_names{i} = [class_names{i} ' (' sprintf('%3.2f',XQC(i)*100) ' %)'];
  if i < size(class_names,1)
    XQC2_class_names{i} = [class_names{i} ' (' sprintf('%3.2f',XQC2(i)*100) ' %)'];
  end;
end;

%% 5.0 Reorder data if needed
[X, i] = sort(X);
X_class_names = X_class_names(i);
[XQC, i] = sort(XQC);
XQC_class_names = XQC_class_names(i);
[XQC2, i] = sort(XQC2);
XQC2_class_names = XQC2_class_names(i);

%% 5.1 Plot pie chart
figure(1); clf(1);
pie(X,X_class_names);
title([cfg.meta.cruise ' - ' cfg.process.selection_name ' - All']);
figure(2); clf(2);
pie(XQC,XQC_class_names);
title([cfg.meta.cruise ' - ' cfg.process.selection_name ' - QC']);
figure(3); clf(3);
pie(XQC2,XQC2_class_names);
title([cfg.meta.cruise ' - ' cfg.process.selection_name ' - QC without unclassified']);

%% 6. Export for javascript figure
fid = fopen([cfg.path.wk 'ClassDistribution.json'], 'w');
buffer = '[';
for i=1:size(X,1)-1
  buffer = [buffer sprintf('{"label":"%s","value":%d},', class_names{i}, countQC(i))];
end;
buffer = [buffer(1:end-1) ']'];
fprintf(fid, '%s', buffer);
fclose(fid); 