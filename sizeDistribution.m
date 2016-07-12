% Size distribution
% created: July 7, 2016
% author: Nils Haentjens

% 0. Parameters
cfg.filename = 'default.cfg';
% Feature to load
% 2:Area    3:BioVolume
cfg_feature.name = 'BioVolume';
cfg_feature.column = 3;
cfg_feature.import = false;
% Bin to plot
cfg_bin.dt.begin_str='D20160511T153155';
cfg_bin.dt.end_str='D20160604T155803';
cfg_plot.n_max = 10;
% cfg_plot.Dmin = 700; % minimum is 1
% cfg_plot.Dmax = 300000;
cfg_plot.Dmin = 5;
cfg_plot.Dmax = 150;
cfg_plot.Dauto = false; % if true does not take Dmin and Dmax into account
cfg_plot.x_log_scale = true;
cfg_plot.y_log_scale = true;

% 1. Load configuration
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
addpath([cfg.path.ifcb_analysis 'feature_extraction' filesep])
fprintf('Done\n');

% 2. Import/Load features
if cfg_feature.import
  fprintf('Importing feature %s... ', cfg_feature.name);  tic;% ~2 min
  cfg.path.wk_features=[cfg.path.wk 'features' filesep];
  bins=dir([cfg.path.wk_features 'D*_fea_v2.csv']);
  bins={bins(:).name}; n = size(bins,2);
  dt=NaN(n,1); ftr=cell(n,1);
  range2read = [1 (cfg_feature.column - 1) -1 (cfg_feature.column - 1)];
  if cfg.proc.parallel
    parfor i=1:n
      ftr{i} = dlmread([cfg.path.wk_features bins{i}], ',', range2read);
      dt(i)=datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
    end;
  else
    for i=1:n
      ftr{i} = dlmread([cfg.path.wk_features bins{i}], ',', range2read);
      dt(i)=datenum(bins{i}(2:16), 'yyyymmddTHHMMSS');
    end;
  end
  save([cfg.path.wk 'feature_' cfg_feature.name], 'dt', 'ftr');
  fprintf('Done\n'); toc;
else
  fprintf('Loading feature %s... ', cfg_feature.name);
  load([cfg.path.wk 'feature_' cfg_feature.name]);
  fprintf('Done\n');
end;

% 3. Plot
fprintf('Plotting... ');
% Get selection of bin
cfg_bin.dt.begin=datenum(cfg_bin.dt.begin_str(2:end), 'yyyymmddTHHMMSS');
cfg_bin.dt.end=datenum(cfg_bin.dt.end_str(2:end), 'yyyymmddTHHMMSS');
sel = find(cfg_bin.dt.begin <= dt & dt <= cfg_bin.dt.end);
% Get log distribution
if cfg_plot.Dauto
  Dmin = ftr{sel(1)}(1); Dmax = ftr{sel(1)}(1);
  for i=sel';
    Dmin = min(Dmin, min(ftr{i}));
    Dmax = max(Dmax, max(ftr{i}));
  end;
  if Dmin == 0; Dmin = 1; end;
else
  Dmin=cfg_plot.Dmin; Dmax=cfg_plot.Dmax;
end;
Nmax = cfg_plot.n_max; N = 1:Nmax;
q=exp(1/Nmax*log(Dmax/Dmin));
D=Dmin*q.^N; D(end) = D(end) * 1.000000001;
% Build histogram with matlab
ftr_all = [];
for i=sel'; ftr_all(end + 1:end + size(ftr{i},1)) = ftr{i}; end;
figure(1);
histogram((6 .* ftr_all) .^ (1/3), D); % Compute size from BioVolume
% xlabel(cfg_feature.name);
xlabel('Diameter (\mum)');
ylabel('Number of cells');
title(sprintf('%s - %s', cfg.meta.cruise, cfg.meta.instrument));
if cfg_plot.x_log_scale;
  x_lim = xlim(); set(gca,'XScale','log'); xlim(x_lim);
end;
if cfg_plot.y_log_scale;
  y_lim = ylim(); set(gca,'YScale','log'); ylim(y_lim);
end;
fprintf('Done\n');
% % Build histogram manually
% count = nan(size(sel,1), Nmax - 1);
% for i=sel';
%   for j=N(1:end-1);
%     count(i, j) = length(find(D(j) <= ftr{i} & ftr{i} <= D(j + 1)));
%   end;
% end;
% count_total=sum(count);
% % Plot
% fig(1);
% bar(D(1:end-1), count_total);
% xlabel(cfg_feature.name);
% ylabel('Number of particules');