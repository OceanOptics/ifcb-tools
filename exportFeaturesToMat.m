% Export features computed by the main script to matlab format files
%   Features must be computed
%   ADC and HDR files must be available
%   metadata.csv must be available

% author: Nils
% created: Jan 18, 2018

clear

%% 1. Load configuration
cfg.filename = 'default.cfg';
fprintf('Loading configuration... ');
addpath('helpers');
cfg = loadCfg(cfg.filename);
addpath([cfg.path.ifcb_analysis 'IFCB_tools' filesep])
if cfg.process.parallel; parfor_arg = Inf; else; parfor_arg = 0; end
fprintf('Done\n');

%% Get features
fprintf('Importing features ... ');  tic;% ~2 min
ftr_bins=dir([cfg.path.features 'D*_fea_v2.csv']);
ftr_bins={ftr_bins(:).name}; n = size(ftr_bins,2);
bin=cell(n,1); dt=NaN(n,1); foo=cell(n,1); roiId = cell(n,1);
% Load data in parallel
parfor (i=1:n, parfor_arg)
% ftr column: 1 summedArea 2 summedBiovolume 3 summedConvexArea 4 summedConvexPerimeter
%             5 summedFeretDiameter 6 summedMajorAxisLength 7 summedMinorAxisLength 8 summedPerimeter
% For more check list of features at: https://github.com/hsosik/ifcb-analysis/wiki/feature-file-documentation
  roiId{i} = dlmread([cfg.path.features ftr_bins{i}], ',', [1 0 -1 0]);
  foo{i} = dlmread([cfg.path.features ftr_bins{i}], ',', [1 35-1 -1 42-1]); % reading all summed features (considering all the blobs of the image)
  dt(i) = datenum(ftr_bins{i}(2:16), 'yyyymmddTHHMMSS');
  bin{i} = ftr_bins{i}(1:24);
end
% Make ftr table
ftr = table(cell(n,1), cell(n,1), cell(n,1), cell(n,1), cell(n,1),...
            cell(n,1), cell(n,1), cell(n,1), cell(n,1),...
            'VariableNames', {'ROIid', 'Area', 'Biovolume', 'ConvexArea', 'ConvexPerimeter',...
            'FeretDiameter', 'MajorAxisLength', 'MinorAxisLength', 'Perimeter', });
ftr.Properties.VariableUnits = {'', 'pixels^2', 'pixels^3', 'pixels^2', 'pixels', 'pixels', 'pixels', 'pixels', 'pixels'};
for i=1:n
  ftr.ROIid{i} = roiId{i};
  ftr.Area{i} = foo{i}(:,1);
  ftr.Biovolume{i} = foo{i}(:,2);
  ftr.ConvexArea{i} = foo{i}(:,3);
  ftr.ConvexPerimeter{i} = foo{i}(:,4);
  ftr.FeretDiameter{i} = foo{i}(:,5);
  ftr.MajorAxisLength{i} = foo{i}(:,6);
  ftr.MinorAxisLength{i} = foo{i}(:,7);
  ftr.Perimeter{i} = foo{i}(:,8);
end
fprintf('Done\n'); toc;

%% Compute additional features
% For each individual sample
foo2=cell(n,1);
parfor (i=1:n, parfor_arg)
% for i=1:n
  % add_ftr columns: 1 ESD from Area      2 ESD from Biovolume 
  %                  3 Perimeter / Area
  foo2{i} = [sqrt(4/pi * foo{i}(:,1)), (6/pi .* foo{i}(:,2)) .^ (1/3),...
             foo{i}(:,8) ./ foo{i}(:,1)];
end
ftr_add =table(cell(n,1), cell(n,1), cell(n,1), NaN(n,1), 'VariableNames',...
               {'ESDA', 'ESDV', 'PA', 'PSDSlope'});
ftr_add.Properties.VariableUnits = {'pixels', 'pixels', '1/pixels', 'None'};
for i=1:n
ftr_add.ESDA{i} = foo2{i}(:,1);
ftr_add.ESDV{i} = foo2{i}(:,2);
ftr_add.PA{i} = foo2{i}(:,3);
end
% For each bin
pixel2um = cfg.meta.resolution_pixel_per_micron;
foo = NaN(n,1);
parfor (i=1:n, parfor_arg)
  foo(i) = find_psd_slope(foo2{i}(:,2) / pixel2um);
end
ftr_add.PSDSlope = foo;

%% Get hdr data
fprintf('Importing header ... ');  tic;% ~2 min
hdr = array2table(NaN(n,6), 'VariableNames', {'VolumeSampled', 'PMTtriggerSelection',...
                  'PMTAhighVoltage', 'PMTBhighVoltage', 'PMTAtriggerThreshold', 'PMTBtriggerThreshold'});
hdr.Properties.VariableUnits = {'mL', '', '', '', '', ''};
for i=1:n
  % Import hdr file
  d = importHDR([cfg.path.in bin{i} '.hdr']);
  % Compute volume sampled based on IFCB_volume_analyzed function
  flowrate = 0.25; %milliliters per minute for syringe pump
  if ~isempty(d)
      looktime = d.runTime - d.inhibitTime; %seconds
      hdr.VolumeSampled(i) = flowrate.*looktime/60;
  end
  hdr.PMTtriggerSelection(i) = d.PMTtriggerSelection_DAQ_MCConly; % 0: None, 1: PMTA, 2: PMTB, 3: PMTA & PMTB
  hdr.PMTAhighVoltage(i) = d.PMTAhighVoltage;
  hdr.PMTBhighVoltage(i) = d.PMTBhighVoltage;
  hdr.PMTAtriggerThreshold(i) = d.PMTAtriggerThreshold_DAQ_MCConly;
  hdr.PMTBtriggerThreshold(i) = d.PMTBtriggerThreshold_DAQ_MCConly;
end
fprintf('Done\n'); toc

%% Get adc data
fprintf('Importing adc ... ');  tic;% ~2 min
foo3 = cell(n, 1);
parfor (i=1:n, parfor_arg)
  d = importADC([cfg.path.in bin{i} '.adc']);
  % adc = {'FluoPeak', 'FluoInt', 'ScatPeak', 'ScatInt'};
  foo3{i} = [d.itrigger, d.PMTA, d.PMTB, d.peakA, d.peakB];
end
% Synchronize ADC and FTR data
% ROI number on FTR correspond to the line number of the ADC
% Trick ADC comports n identical lines when n roi are selected on one
% image. If n > 1 then the peak A and B are for one of the ROI and PMT A
% and B are for one of the ROI only but which one ??? Probably the one
% closest to the most probable spot.
% They might be ADC for which there is no ROI, the particle that trigger
% was not detected by the camera.
adc = array2table(cell(n,5), 'VariableNames', {'ScatInt', 'FluoInt', ...
                  'ScatPeak', 'FluoPeak', 'NumberOfROIinTrigger'});
for i = 1:n
 adc.ScatInt{i} = foo3{i}(ftr.ROIid{i}, 2);
 adc.FluoInt{i} = foo3{i}(ftr.ROIid{i}, 3);
 adc.ScatPeak{i} = foo3{i}(ftr.ROIid{i}, 4);
 adc.FluoPeak{i} = foo3{i}(ftr.ROIid{i}, 5);
 adc.NumberOfROIinTrigger{i} = sum(foo3{i}(ftr.ROIid{i}, 1) == foo3{i}(ftr.ROIid{i}, 1)')';
end
fprintf('Done\n'); toc;

%% Get metadata
fprintf('EDIT importMetadata TO GET stn_id AS number or string.\n');
md = importMetadata(cfg.path.meta);
% Sync metadata index on bin
[~, i] = intersect(md.id, bin);
md = md(i,:);
% Check sync
for i=1:n
  if ~strcmp(md.id(i), bin{i})
    fprintf('ERROR: Sync failed at index %d\n', i);
  end
end

%% Build full tables
ifcb = [md hdr ftr ftr_add adc];
save([cfg.path.wk 'meta_hdr_ftr_adc.mat'], 'ifcb');
% load([cfg.path.wk 'meta_hdr_ftr_adc.mat'], 'ifcb');

%% Build light table
% keep only good inline
row_sel = strcmp(ifcb.type,'inline') & ifcb.flag == 1 & ifcb.concentration == 1;
col_sel = strcmp(ifcb.Properties.VariableNames, 'dt') | ...
            strcmp(ifcb.Properties.VariableNames, 'lat') | strcmp(ifcb.Properties.VariableNames, 'lon') | ...
            strcmp(ifcb.Properties.VariableNames, 'stn_id') | strcmp(ifcb.Properties.VariableNames, 'VolumeSampled') | ...
            strcmp(ifcb.Properties.VariableNames, 'Area') | strcmp(ifcb.Properties.VariableNames, 'Biovolume') | ...
            strcmp(ifcb.Properties.VariableNames, 'Perimeter') | ...
            strcmp(ifcb.Properties.VariableNames, 'ESDA') | strcmp(ifcb.Properties.VariableNames, 'ESDV');            
ifcb_inline = ifcb(row_sel, col_sel);
save([cfg.path.wk 'ifcb_inline_features.mat'], 'ifcb_inline');
%% keep only good ctd
row_sel = strcmp(ifcb.type, 'niskin') & ifcb.flag == 1;
col_sel = strcmp(ifcb.Properties.VariableNames, 'dt') | strcmp(ifcb.Properties.VariableNames, 'depth') | ...
            strcmp(ifcb.Properties.VariableNames, 'lat') | strcmp(ifcb.Properties.VariableNames, 'lon') | ...
            strcmp(ifcb.Properties.VariableNames, 'ref') | strcmp(ifcb.Properties.VariableNames, 'stn_id') | ...
            strcmp(ifcb.Properties.VariableNames, 'cast_id') | strcmp(ifcb.Properties.VariableNames, 'source_id') | ...
            strcmp(ifcb.Properties.VariableNames, 'VolumeSampled') | strcmp(ifcb.Properties.VariableNames, 'concentration') | ...
            strcmp(ifcb.Properties.VariableNames, 'Area') | strcmp(ifcb.Properties.VariableNames, 'Biovolume') | ...
            strcmp(ifcb.Properties.VariableNames, 'Perimeter') | ...
            strcmp(ifcb.Properties.VariableNames, 'ESDA') | strcmp(ifcb.Properties.VariableNames, 'ESDV');
ifcb_ctd = ifcb(row_sel, col_sel);
save([cfg.path.wk 'ifcb_ctd_features.mat'], 'ifcb_ctd');

%% Build table with median and summed Calibrated in-line features
row_sel = strcmp(ifcb.type,'inline') & ifcb.flag == 1 & ifcb.concentration == 1;
col_sel = strcmp(ifcb.Properties.VariableNames, 'dt') | ...
          strcmp(ifcb.Properties.VariableNames, 'lat') | strcmp(ifcb.Properties.VariableNames, 'lon') | ...
          strcmp(ifcb.Properties.VariableNames, 'stn_id');
d = ifcb(row_sel, col_sel);
d.n = cellfun('length', ifcb.Area(row_sel)) / 5;
d.ESD_avg = cellfun(@(x) nanmedian(x), ifcb.ESDV(row_sel)) * 1/3.4; % form pixels to um
d.Area_avg = cellfun(@(x) nanmedian(x), ifcb.Area(row_sel)) * 1/3.4^2; % from pixels^2 to um^2
d.Area_sum = cellfun(@(x) sum(x), ifcb.Area(row_sel)) * 1/3.4^2 * 1e-6^2 * 1/5 * 1e6; % from pixel^2/5 mL to m^2/m^3 = m^-1
d.Biovolume_avg = cellfun(@(x) nanmedian(x), ifcb.Biovolume(row_sel)) * 1/3.4^3; % from pixels^3 to um^3
d.Concentration = cellfun(@(x) sum(x), ifcb.Biovolume(row_sel)) * 1/3.4^3 * 1e-6^3 * 1/5 * 1e6; % from pixel^3/5 mL to m^3/m^3 = unitless
d.PA_avg = cellfun(@(x) nanmean(x), ifcb.PA(row_sel)) * 3.4; % from pixels/pixels^2 to um/um^2
d.PSDSlope = ifcb.PSDSlope(row_sel);
d.Properties.VariableUnits = {'Matlab datenum', 'deg N', 'deg E', 'None', '#/mL', 'um', 'um^2', 'um^2', 'um^3', 'm^3/m^3', '1/m', 'None'};
save([cfg.path.wk 'ifcb_inline_prod.mat'], 'd');
% writetable(d, [cfg.path.wk 'ifcb_inline_prod.csv']);
%% Build table with median and summed Calibrated niskin features
row_sel = strcmp(ifcb.type,'niskin') & ifcb.flag == 1 & ifcb.concentration == 1;
col_sel = strcmp(ifcb.Properties.VariableNames, 'dt') | ...
          strcmp(ifcb.Properties.VariableNames, 'lat') | strcmp(ifcb.Properties.VariableNames, 'lon') | ...
          strcmp(ifcb.Properties.VariableNames, 'stn_id') | strcmp(ifcb.Properties.VariableNames, 'cast_id') |...
          strcmp(ifcb.Properties.VariableNames, 'source_id') | strcmp(ifcb.Properties.VariableNames, 'depth');
d = ifcb(row_sel, col_sel);
d.n = cellfun('length', ifcb.Area(row_sel)) / 5;
d.ESD_avg = cellfun(@(x) nanmedian(x), ifcb.ESDV(row_sel)) * 1/3.4; % form pixels to um
d.Area_avg = cellfun(@(x) nanmedian(x), ifcb.Area(row_sel)) * 1/3.4^2; % from pixels^2 to um^2
d.Area_sum = cellfun(@(x) sum(x), ifcb.Area(row_sel)) * 1/3.4^2 * 1e-6^2 * 1/5 * 1e6; % from pixel^2/5 mL to m^2/m^3 = m^-1
d.Biovolume_avg = cellfun(@(x) nanmedian(x), ifcb.Biovolume(row_sel)) * 1/3.4^3; % from pixels^3 to um^3
d.Concentration = cellfun(@(x) sum(x), ifcb.Biovolume(row_sel)) * 1/3.4^3 * 1e-6^3 * 1/5 * 1e6; % from pixel^3/5 mL to m^3/m^3 = unitless
d.PA_avg = cellfun(@(x) nanmean(x), ifcb.PA(row_sel)) * 3.4; % from pixels/pixels^2 to um/um^2
d.PSDSlope = ifcb.PSDSlope(row_sel);
d.Properties.VariableUnits = {'Matlab datenum', 'deg N', 'deg E', 'm', 'None', 'None', 'None', '#/mL', 'um', 'um^2', 'um^2', 'um^3', 'm^3/m^3', '1/m', 'None'};
save([cfg.path.wk 'ifcb_niskin_prod.mat'], 'd');
% writetable(d, [cfg.path.wk 'ifcb_niskin_prod.csv']);
%% Check Volume Sampled
fig(3); plot(ifcb_inline.dt, ifcb_inline.VolumeSampled);
datetick();
ylabel('Volume Sampled (mL)');
median(ifcb_inline.VolumeSampled);
set(datacursormode(figure(3)),'UpdateFcn',@data_cursor_display_date);

%% Check PSD Slope
fig(4); plot(ifcb.dt, ifcb.PSDSlope);
datetick2_doy();
ylabel('PSD Slope');
set(datacursormode(figure(4)),'UpdateFcn',@data_cursor_display_date);

fig(5); hold('on');
for i=1:1565
  [slope, intercept, psd, bin_means] = find_psd_slope(ifcb.ESDV{i} / pixel2um);
  x = bin_means(1):bin_means(end);
  plot(bin_means, psd, 's',x, intercept*(5./x).^slope);
end
%% 
