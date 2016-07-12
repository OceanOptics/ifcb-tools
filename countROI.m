% Count number of ROI


cfg.filename = 'default.cfg';

% 1. Load configuration
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
addpath([cfg.path.ifcb_analysis 'feature_extraction' filesep])
fprintf('Done\n');

% 2. Run through all the files
bins=dir([cfg.path.in 'D*.adc']);
bins={bins(:).name};
dt=NaN(size(bins,2),1); counts=dt;
if cfg.proc.parallel
  parfor i=1:size(bins,2);
    fprintf('%s count_ROI %s\n', utcdate(now()), bins{i});
    dt(i,1)=datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
    counts(i,1)=getNumberROI([cfg.path.in bins{i}]);
  end;
else
  for i=1:size(bins,2);
    fprintf('%s count_ROI %s... ', utcdate(now()), bins{i});
    dt(i,1)=datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
    counts(i,1)=getNumberROI([cfg.path.in bins{i}]);
    fprintf('Done\n');
  end;
end;

% 3. Export counts
cfg.path.wk_counts=[cfg.path.wk 'counts.csv'];
csvwrite(cfg.path.wk_counts, [datevec(dt), counts]);
