% Size distribution
% created: July 7, 2016
% author: Nils Haentjens

% 0. Load configuration
cfg.filename = 'default.cfg';
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
fprintf('Done\n');

% 1. Parameters
% Feature to load
% 2:Area    3:BioVolume
% Diameter is estimated from BioVolume (column=3; name='Diameter')
cfg.feature.name = 'Diameter';
cfg.feature.units = '\mum';
cfg.feature.column = 3;
cfg.feature.import = false;
% Bin to plot
% cfg.bin.dt.begin_str='D20160511T153155';
% cfg.bin.dt.end_str='D20160604T155803';
cfg.bin.selection = [cfg.path.wk 'selection/station_inline_4.csv']; % inline.csv
cfg.bin.period = 'May 2016';
cfg.plot.normalize = true;
cfg.plot.n_max = 20;
% cfg.plot.Dmin = 700; % minimum is 1
% cfg.plot.Dmax = 300000;
cfg.plot.Dmin = 5;
cfg.plot.Dmax = 150;
cfg.plot.Dauto = false; % if true does not take Dmin and Dmax into account
cfg.plot.x_log_scale = true;
cfg.plot.y_log_scale = false;
% cfg.plot.y_lim = [1; 2e6];
cfg.plot.save = false;
cfg.export.save = false;
cfg.export.name = 'stn4';

% 2. Import/Load features
if cfg.feature.import
  fprintf('Importing features %s... ', cfg.feature.name);  tic;% ~2 min
  cfg.path.wk_features=[cfg.path.wk 'features' filesep];
  bins=dir([cfg.path.wk_features 'D*_fea_v2.csv']);
  bins={bins(:).name}; n = size(bins,2);
  bin=cell(n,1); dt=NaN(n,1); ftr=cell(n,1);
  range2read = [1 (cfg.feature.column - 1) -1 (cfg.feature.column - 1)];
  if cfg.proc.parallel
    parfor i=1:n
      ftr{i} = dlmread([cfg.path.wk_features bins{i}], ',', range2read);
      dt(i) = datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
      bin{i} = bins{i}(1:24);
    end;
  else
    for i=1:n
      ftr{i} = dlmread([cfg.path.wk_features bins{i}], ',', range2read);
      dt(i) = datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
      bin{i} = bins{i}(1:24);
    end;
  end
  if cfg.feature.column == 3 && strcmp(cfg.feature.name, 'Diameter');
    if cfg.proc.parallel
      parfor i=1:n; ftr{i} = (6 .* ftr{i}) .^ (1/3); end;
    else
      for i=1:n; ftr{i} = (6 .* ftr{i}) .^ (1/3); end;
    end
  end;
  save([cfg.path.wk 'features_' cfg.feature.name], 'dt', 'ftr', 'bin');
  fprintf('Done\n'); toc;
else
  fprintf('Loading features %s... ', cfg.feature.name);
  load([cfg.path.wk 'features_' cfg.feature.name]);
  fprintf('Done\n');
end;

% 3. Selecting data
fprintf('Filtering... ');
% Get selection of bin
if isfield(cfg.bin, 'selection')
  % load file with selection
  f = fopen(cfg.bin.selection);
  data = textscan(f, '%s', 'Delimiter', ',');
  fclose(f); data = data{1};
  sel = [];
  for i = 1:size(data,1);
    foo = find(not(cellfun('isempty',(strfind(bin, data{i})))));
    if ~isempty(foo); sel(end+1,1) = foo; end;
  end;
elseif isfield(cfg.bin, 'dt')
  cfg.bin.dt.begin=datenum(cfg.bin.dt.begin_str(2:end), 'yyyymmddTHHMMSS');
  cfg.bin.dt.end=datenum(cfg.bin.dt.end_str(2:end), 'yyyymmddTHHMMSS');
  sel = find(cfg.bin.dt.begin <= dt & dt <= cfg.bin.dt.end);
else
  fprintf('Selecting all data\n');
  sel = 1:size(bin, 1);
end;
fprintf('Done\n');

% 4. Plot histogram
fprintf('Plotting histogram...');
% Get min and max of size
if cfg.plot.Dauto
  Dmin = ftr{sel(1)}(1); Dmax = ftr{sel(1)}(1);
  for i=sel';
    Dmin = min(Dmin, min(ftr{i}));
    Dmax = max(Dmax, max(ftr{i}));
  end;
  if Dmin == 0; Dmin = 1; end;
else
  Dmin=cfg.plot.Dmin; Dmax=cfg.plot.Dmax;
end;
% Get log distribution
Nmax = cfg.plot.n_max; N = 1:Nmax;
q=exp(1/Nmax*log(Dmax/Dmin));
D=Dmin*q.^N; D(end) = D(end) * 1.000000001;
% Build histogram with matlab
ftr_all = [];
for i=sel'; ftr_all(end + 1:end + size(ftr{i},1)) = ftr{i}; end;
% Plot histogram
figure(10); clf(10);
% hold('on');
if cfg.plot.normalize;
  histogram(ftr_all, D, 'Normalization', 'probability');
  ylabel('Normalized (number of cells)');
else
  histogram(ftr_all, D);
  ylabel('Number of cells');
end;
% Set label + title
xlabel([cfg.feature.name ' (' cfg.feature.units ')']);
title(sprintf('%s - %s', cfg.meta.cruise, cfg.meta.instrument));
% Set y limit
if isfield(cfg.plot, 'y_lim'); ylim(cfg.plot.y_lim); end;
% Set scale
if cfg.plot.x_log_scale;
  x_lim = xlim(); set(gca,'XScale','log'); xlim(x_lim);
end;
if cfg.plot.y_log_scale;
  y_lim = ylim(); set(gca,'YScale','log'); ylim(y_lim);
end;
fprintf('Done\n');
% Save figure
if cfg.plot.save;
  dir_fig = [cfg.path.wk 'fig/'];
  if ~isdir(dir_fig); mkdir(dir_fig); end;
  set(gcf,'PaperUnits','centimeters','PaperPosition',[0 0 21 21]);
  print('-dpng', '-r300', sprintf('%s/SizeDistributionNormalized', dir_fig));
end;

%% 5. Plot time series
fprintf('Plotting time series...');
figure(11); clf(11);
% Compute median of feature for each bin
y = []; y_std = []; y_pt25 = []; y_pt75=[]; n=[]; y_tot=[];
for i=sel';
  y(end+1,1) = median(ftr{i});
  y_std(end+1,1) = std(ftr{i});
  y_pt25(end+1,1)=prctile(ftr{i}, 25);
  y_pt75(end+1,1)=prctile(ftr{i}, 75);
  y_tot(end+1, 1)= sum(ftr{i});
  n(end+1,1) = size(ftr{i},1);
end;
% Plot left
yyaxis('left')
plot(dt(sel), y, '--o');
% hold('on'); plot(dt(sel), y_pt25, dt(sel), y_pt75);
% errorbar(dt(sel), y, y_std);
ylabel(['Median ' cfg.feature.name ' (' cfg.feature.units ')' ]);
% Plot number of ROI
yyaxis('right');
plot(dt(sel), n, 'd');
datetick('x', 'ddd-HH:MM');
set(gca, 'XTickLabelRotation', 45);
ylabel('Number of ROI');
% xlim([datenum(2016,05,24,04,00,00), datenum(2016,05,29,03,00,00)]);
xlabel(cfg.bin.period);
% Save figure
fprintf('Done\n');
if cfg.plot.save;
  dir_fig = [cfg.path.wk 'fig/'];
  if ~isdir(dir_fig); mkdir(dir_fig); end;
  set(gcf,'PaperUnits','centimeters','PaperPosition',[0 0 21 15]);
  print('-dpng', '-r300', sprintf('%s/SizeDistributionOverTime', dir_fig));
end;

%% Export data
if cfg.export.save
  x_dt=dt(sel);
  y_med=y;
  save([cfg.path.wk 'sizeDistributionTS_' cfg.feature.name '_' cfg.export.name], 'x_dt', 'y_*', 'n');
end;