% Check exported data for EcoTaxa
%   Look for NaN, infinit, or >float32 values.
% author: Nils Haëntjens
% created: May 2, 2016

%% 0. Load configuration
cfg.filename = 'default.cfg';
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
  ftr_names = {'roi_number','Area','Biovolume','BoundingBox_xwidth','BoundingBox_ywidth','ConvexArea','ConvexPerimeter','Eccentricity','EquivDiameter','Extent','FeretDiameter','H180','H90','Hflip','MajorAxisLength','MinorAxisLength','Orientation','Perimeter','RWcenter2total_powerratio','RWhalfpowerintegral','Solidity','moment_invariant1','moment_invariant2','moment_invariant3','moment_invariant4','moment_invariant5','moment_invariant6','moment_invariant7','numBlobs','shapehist_kurtosis_normEqD','shapehist_mean_normEqD','shapehist_median_normEqD','shapehist_mode_normEqD','shapehist_skewness_normEqD','summedArea','summedBiovolume','summedConvexArea','summedConvexPerimeter','summedFeretDiameter','summedMajorAxisLength','summedMinorAxisLength','summedPerimeter','texture_average_contrast','texture_average_gray_level','texture_entropy','texture_smoothness','texture_third_moment','texture_uniformity','RotatedArea','RotatedBoundingBox_xwidth','RotatedBoundingBox_ywidth','Wedge01','Wedge02','Wedge03','Wedge04','Wedge05','Wedge06','Wedge07','Wedge08','Wedge09','Wedge10','Wedge11','Wedge12','Wedge13','Wedge14','Wedge15','Wedge16','Wedge17','Wedge18','Wedge19','Wedge20','Wedge21','Wedge22','Wedge23','Wedge24','Wedge25','Wedge26','Wedge27','Wedge28','Wedge29','Wedge30','Wedge31','Wedge32','Wedge33','Wedge34','Wedge35','Wedge36','Wedge37','Wedge38','Wedge39','Wedge40','Wedge41','Wedge42','Wedge43','Wedge44','Wedge45','Wedge46','Wedge47','Wedge48','Ring01','Ring02','Ring03','Ring04','Ring05','Ring06','Ring07','Ring08','Ring09','Ring10','Ring11','Ring12','Ring13','Ring14','Ring15','Ring16','Ring17','Ring18','Ring19','Ring20','Ring21','Ring22','Ring23','Ring24','Ring25','Ring26','Ring27','Ring28','Ring29','Ring30','Ring31','Ring32','Ring33','Ring34','Ring35','Ring36','Ring37','Ring38','Ring39','Ring40','Ring41','Ring42','Ring43','Ring44','Ring45','Ring46','Ring47','Ring48','Ring49','Ring50','HOG01','HOG02','HOG03','HOG04','HOG05','HOG06','HOG07','HOG08','HOG09','HOG10','HOG11','HOG12','HOG13','HOG14','HOG15','HOG16','HOG17','HOG18','HOG19','HOG20','HOG21','HOG22','HOG23','HOG24','HOG25','HOG26','HOG27','HOG28','HOG29','HOG30','HOG31','HOG32','HOG33','HOG34','HOG35','HOG36','HOG37','HOG38','HOG39','HOG40','HOG41','HOG42','HOG43','HOG44','HOG45','HOG46','HOG47','HOG48','HOG49','HOG50','HOG51','HOG52','HOG53','HOG54','HOG55','HOG56','HOG57','HOG58','HOG59','HOG60','HOG61','HOG62','HOG63','HOG64','HOG65','HOG66','HOG67','HOG68','HOG69','HOG70','HOG71','HOG72','HOG73','HOG74','HOG75','HOG76','HOG77','HOG78','HOG79','HOG80','HOG81','Area_over_PerimeterSquared','Area_over_Perimeter','H90_over_Hflip','H90_over_H180','Hflip_over_H180','summedConvexPerimeter_over_Perimeter','rotated_BoundingBox_solidity'};
  save([cfg.path.wk 'features_all'], 'dt', 'ftr', 'bin', 'ftr_names', saveopt);
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
flagged_index = find(flagged)';
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
      
