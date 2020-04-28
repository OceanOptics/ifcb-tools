% Plot PSD from exportFeaturesToMat.m
% author: nils
% created: June 11, 2019


cfg.filename = 'cfg/OO2019.cfg';

%% 1. Load configuration
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
fprintf('Done\n');

%% 2. Load features
load([cfg.path.wk 'meta_hdr_ftr_adc.mat']);

%% 3. Calibrate data
IFCB_RESOLUTION = 3.4;
fprintf('Calibrating ... ');
ifcb.Area = cellfun(@(x) x * 1/IFCB_RESOLUTION^2, ifcb.Area, 'UniformOutput', false);
ifcb.Biovolume = cellfun(@(x) x * 1/IFCB_RESOLUTION^3, ifcb.Biovolume, 'UniformOutput', false);
ifcb.ConvexArea = cellfun(@(x) x * 1/IFCB_RESOLUTION^2, ifcb.ConvexArea, 'UniformOutput', false);
ifcb.ConvexPerimeter = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.ConvexPerimeter, 'UniformOutput', false);
ifcb.FeretDiameter = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.FeretDiameter, 'UniformOutput', false);
ifcb.MajorAxisLength = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.MajorAxisLength, 'UniformOutput', false);
ifcb.MinorAxisLength = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.MinorAxisLength, 'UniformOutput', false);
ifcb.Perimeter = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.Perimeter, 'UniformOutput', false);
ifcb.ESDA = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.ESDA, 'UniformOutput', false);
ifcb.ESDV = cellfun(@(x) x * 1/IFCB_RESOLUTION, ifcb.ESDV, 'UniformOutput', false);
ifcb.PA = cellfun(@(x) x * IFCB_RESOLUTION, ifcb.PA, 'UniformOutput', false);
% Change units
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'Area')} = 'um^2';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'Biovolume')} = 'um^3';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'ConvexArea')} = 'um^2';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'ConvexPerimeter')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'FeretDiameter')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'MajorAxisLength')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'MinorAxisLength')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'Perimeter')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'ESDA')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'ESDV')} = 'um';
ifcb.Properties.VariableUnits{strcmp(ifcb.Properties.VariableNames, 'PA')} = '1/um';
fprintf('Done\n');

%% 4. Compute PSD
% Cover good IFCB size range (um)
dlim = [3 80]; n = 30;
% Compute log distributed bin edges
q=exp(1/n*log(dlim(2)/dlim(1)));
bin_edges = dlim(1)*q.^(0:n);
% Compute psd
ifcb.PSDSlope(:) = NaN;
ifcb.PSDIntercept(:) = NaN;
ifcb.PSD = cell(height(ifcb),1);
for i=1:height(ifcb)
  [ifcb.PSDSlope(i), ifcb.PSDIntercept(i), ifcb.PSD{i}, bin_means] = find_psd_slope(ifcb.ESDV{i}, bin_edges);
end
% 5. Plot PSDs
figure(1); clf(1); hold('on'); C=brewermap(NaN, 'Paired'); h = [];
for i=1:height(ifcb)
h(end+1) = scatter(bin_means, ifcb.PSD{i}/ifcb.VolumeSampled(i), [], C(i,:), 'filled');
plot(bin_means, ifcb.PSD{i}/ifcb.VolumeSampled(i), '--', 'Color', C(i,:));
% bar(bin_means, ifcb.PSD{i});
% plot(bin_means, ifcb.PSDIntercept(i)*(5./bin_means).^ifcb.PSDSlope(i), 'Color', C(i,:));
end
set(gca, 'XScale', 'log'); % , 'YScale', 'log', 
xlabel('ESD (\mum)');
ylabel('Abundance / Bin Width / Volume Sampled (#/\mum/mL)');
box('on');
legend(h, cellfun(@(x) strrep(x, '_IFCB107', ''), ifcb.id, 'UniformOutput', false));
set(gca, 'XMinorTick', 'off', 'xTick', bin_means(1:4:end) , 'xTickLabel', cellfun(@(x) sprintf('%1.1f', x), num2cell(bin_means(1:4:end)), 'UniformOutput', false)); %, 'XTickLabelRotation', 45
save_fig([cfg.path.wk 'OO2019_IFCB_PSD.svg'], 800, 600);

%% 5. Save data
ifcb.PSDSlope = []; ifcb.PSDIntercept = []; 
save([cfg.path.wk 'OO2019_IFCB_PSD.mat'], 'ifcb', 'bin_edges', 'bin_means');
ifcb.PSD = [];
save([cfg.path.wk 'OO2019_IFCB_data.mat'], 'ifcb');