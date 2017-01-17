% Count number of ROI
% author: Nils Haentjens
% created: May 2016

% 0. Load configuration
cfg.filename = 'default.cfg';
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
fprintf('Done\n');

%% 1. Parameters
cfg.counts.import = true;
cfg.counts.export2csv = false;
cfg.path.wk_selection = [cfg.path.selection cfg.process.selection];

%% 2. Run through all the files
if cfg.counts.import
  fprintf('Importing counts... ');  tic;% ~2 min
  bins=dir([cfg.path.in 'D*.adc']);
  bins={bins(:).name};
  dt=NaN(size(bins,2),1); counts=dt; bin={};
  if cfg.proc.parallel
    parfor i=1:size(bins,2)
      bin{i,1} = bins{i}(1:24);
      dt(i,1)=datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
      counts(i,1)=getNumberROI([cfg.path.in bins{i}]);
    end;
  else
    for i=1:size(bins,2)
      bin{i,1} = bins{i}(1:24);
      dt(i,1)=datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
      counts(i,1)=getNumberROI([cfg.path.in bins{i}]);
    end;
  end;
  if ~isdir(cfg.path.wk); mkdir(cfg.path.wk); end;
  save([cfg.path.wk 'counts'], 'bin', 'dt', 'counts');
  fprintf('Done\n'); toc;  
else
  fprintf('Loading counts... ');
  load([cfg.path.wk 'counts']);
  fprintf('Done\n');
end;

%% 3. Get selection
sel = getSelection(bin, cfg.path.wk_selection);
dt_sel=[]; counts_sel=[];
for i=sel'
  dt_sel(end + 1:end + size(dt(i),1),1) = dt(i);
  counts_sel(end + 1:end + size(counts(i),1),1) = counts(i);
end;

%% 4. Quick plots
figure(11); clf(11);
plot(dt_sel, counts_sel, 'o--');
title([cfg.meta.cruise ' - ' cfg.meta.instrument]);
ylabel('Number of ROI by bin');
datetick('x', 'dd'); xlabel(cfg.meta.period);

% Display number of ROI
fprintf('Number of ROI: %d\n', sum(counts_sel));


%% 5. Export counts
if cfg.counts.export2csv 
  if ~isdir(cfg.path.wk); mkdir(cfg.path.wk); end;
  cfg.path.wk_counts = [cfg.path.wk 'countROI_' cfg.process.selection_name '.csv'];
  csvwrite(cfg.path.wk_counts, [datevec(dt_sel), counts_sel]);
end;
