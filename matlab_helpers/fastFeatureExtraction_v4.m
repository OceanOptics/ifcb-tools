function [features, feature_keys] = fastFeatureExtraction(path_to_bin, bin_name, level, parallel_flag)
% FASTFEATUREEXTRACTION will keep the blob extraction in memory and extract only relevant features
% without writing to disk the blob or the feature table which considerable accelerate the process.
%
% extract same features as features_slim, except keep only the summed features
% 
% Note that if parallel pool needs to be started at each execution of the function, it will be
% faster to run it on a single core

% debug
% data = path_to_bin; bin_name = 'D20180811T034705_IFCB107'; level = 2; parallel_flag = false;

BLOB_FEATURES = 0;
SLIM_FEATURES = 1;
ALL_FEATURES = 2;

if nargin < 4; parallel_flag = false; end
if nargin < 3; level = SLIM_FEATURES; end

if parallel_flag; parflag = Inf; else; parflag = 0; end

% Get images
targets = get_images_fromROI([path_to_bin filesep bin_name '.roi']);
n = length(targets.targetNumber);

% Update config
cfg = configure_test(); % updated for V4
if level ~= BLOB_FEATURES
  % blob_props was updated with v4
  % note that ConvexHull is not supported blob_geomprop, so was removed
  cfg.blob_props = {'Area', 'BoundingBox', 'ConvexArea', 'Eccentricity', 'EquivDiameter', 'Extent', 'MajorAxisLength', ...
                    'MinorAxisLength', 'Orientation', 'Perimeter', 'Solidity'};
end
if level == SLIM_FEATURES
  cfg.props2sum = {}; % Done directly below
end

% Init feature table
switch level
  case BLOB_FEATURES
    features = zeros(n,3, 'uint32');
  case SLIM_FEATURES
    features = NaN(n, 18); 
  case ALL_FEATURES
    features = NaN(n, 235);  % But add 6 fields after
  otherwise
    error('feature level not supported');
end

% Quick parfor acceleration
if n > 0
  targets_image = targets.image;
  targets_targetNumber = targets.targetNumber;
else
  targets_image = {};
  targets_targetNumber = [];
end

parfor(i=1:n, parflag)
% for i=1:length(targets.image)
  % Configure Target
  target = {};
  target.config = cfg;
  target.image = targets_image{i};
  % Get Blob
  target = blob_v4(target); % Updated for V4
  switch level
    case BLOB_FEATURES
      % Output only features that come with blob extraction
      features(i,:) = [targets_targetNumber(i), sum(target.blob_props.Area), target.blob_props.numBlobs];
    case SLIM_FEATURES
      % Get Features
      target = blob_geomprop(target);
      target = blob_rotate(target);    % Added on v4
  %     target = blob_texture(target);
      target = biovolume(target);
      summedArea = sum(target.blob_props.Area);
      summedEquivDiameter = sqrt(4/pi * summedArea);
      features(i,:) = [targets.targetNumber(i), summedArea, target.blob_props.numBlobs, summedEquivDiameter, ...
                           sum([target.blob_props.minFeretDiameter', target.blob_props.maxFeretDiameter',...
                           target.blob_props.MinorAxisLength', target.blob_props.MajorAxisLength',...
                           target.blob_props.Perimeter', target.blob_props.Biovolume',... 
                           target.blob_props.ConvexArea', target.blob_props.ConvexPerimeter',...
                           target.blob_props.SurfaceArea'],1),...
                           target.blob_props.Eccentricity(1), target.blob_props.Extent(1),...
                           target.blob_props.Orientation(1), target.blob_props.RepresentativeWidth(1),...
                           target.blob_props.Solidity(1)];
    case ALL_FEATURES
%       if targets.targetNumber(i) == 2077  % For debugging
%         fprintf('%5d - %5d\n', i, targets.targetNumber(i));
%       end
      % Get Features
      target = blob_geomprop(target);
      target = blob_rotate(target);
      target = blob_texture(target);  % Need DIPUM
      target = blob_invmoments(target);
      target = blob_shapehist_stats(target);  % Need to patch function line 19 with: if size(x,2) > 1; x = x'; y=y'; end to correct bug in case of 1D perimeter
      target = blob_RingWedge(target);
      target = biovolume(target);
      target = blob_sumprops(target);
      target = blob_Hausdorff_symmetry(target);
      target = blob_binary_symmetry(target);
      target = image_HOG(target);
      target = blob_rotated_geomprop(target);
      % Format
      Wedges = target.blob_props.Wedges;
      Rings = target.blob_props.Rings;
      HOG = target.image_props.HOG;
      target_features = rmfield(target.blob_props, {'Rings', 'Wedges'});
%       feature_keys = [{'PID'}; fieldnames(target_features);
%                         cellstr([repmat('Wedge',length(Wedges),1) num2str((1:length(Wedges))','%02d')]);
%                         cellstr([repmat('Ring',length(Rings),1) num2str((1:length(Rings))','%02d')]);
%                         cellstr([repmat('HOG',length(HOG),1) num2str((1:length(HOG))','%02d')])];
      if target_features.numBlobs > 1
        % In case multiple blobs only keep largest one
        f = fieldnames(target_features)';
        for k=1:length(f)
          % Assumes first is the largest (as sorted in blob_geomprop)
          if length(target_features.(f{k})) > 1
            target_features.(f{k}) = target_features.(f{k})(1);
          end
        end
      end
      features(i,:) = [targets.targetNumber(i);
                       cell2mat(struct2cell(target_features));  % HOG is only property in image_props
                       Wedges; Rings; HOG]';
    otherwise
      error('feature level not supported');
  end
end

if level == ALL_FEATURES
  % Add Derived Features
  a = 2; b = 12;
%   a = strmatch('Area', feature_keys, 'exact'); b = strmatch('Perimeter', feature_keys, 'exact'); 
  features = [features, features(:,a)./features(:,b).^2, features(:,a)./features(:,b)]; %A/P^2 compactness or circularity index; A/P roundness index
%   feature_keys = [feature_keys; 'Area_over_PerimeterSquared'; 'Area_over_Perimeter'];
  a = 50; b = 49; c = 48;
%   a = strmatch('Hflip', feature_keys, 'exact'); b = strmatch('H90', feature_keys, 'exact'); c = strmatch('H180', feature_keys, 'exact'); 
  features = [features, features(:,b)./features(:,a), features(:,b)./features(:,c), features(:,a)./features(:,c)]; %A/P^2 compactness or circularity index; A/P roundness index
%   feature_keys = [feature_keys; 'H90_over_Hflip'; 'H90_over_H180'; 'Hflip_over_H180'];
  a = 43; b = 46; 
%   a = strmatch('summedConvexPerimeter', feature_keys, 'exact'); b = strmatch('summedPerimeter', feature_keys, 'exact'); 
  features = [features, features(:,a)./features(:,b)]; 
%   feature_keys = [feature_keys; 'summedConvexPerimeter_over_Perimeter'];
end

% Output features names
if nargout == 2
  switch level
    case BLOB_FEATURES
      feature_keys = {'PID', 'Area', 'NumberBlobs'};
    case SLIM_FEATURES
      feature_keys = {'PID', 'Area', 'NumberBlobs', 'EquivDiameter', 'MinFeretDiameter', 'MaxFeretDiameter', 'MinorAxisLength', 'MajorAxisLength', 'Perimeter', 'Biovolume',...
                    'ConvexArea', 'ConvexPerimeter', 'SurfaceArea', 'Eccentricity', 'Extent', 'Orientation', 'RepresentativeWidth', 'Solidity'};
    case ALL_FEATURES
      feature_keys = {'PID','Area','numBlobs','MajorAxisLength','MinorAxisLength','Eccentricity','Orientation','ConvexArea','EquivDiameter','Solidity','Extent','Perimeter','ConvexPerimeter','maxFeretDiameter','minFeretDiameter','BoundingBox_xwidth','BoundingBox_ywidth','texture_average_gray_level','texture_average_contrast','texture_smoothness','texture_third_moment','texture_uniformity','texture_entropy','moment_invariant1','moment_invariant2','moment_invariant3','moment_invariant4','moment_invariant5','moment_invariant6','moment_invariant7','shapehist_mean_normEqD','shapehist_median_normEqD','shapehist_skewness_normEqD','shapehist_kurtosis_normEqD','RWhalfpowerintegral','RWcenter2total_powerratio','Biovolume','SurfaceArea','RepresentativeWidth','summedArea','summedBiovolume','summedConvexArea','summedConvexPerimeter','summedMajorAxisLength','summedMinorAxisLength','summedPerimeter','summedSurfaceArea','H180','H90','Hflip','B180','B90','Bflip','RotatedBoundingBox_xwidth','RotatedBoundingBox_ywidth','rotated_BoundingBox_solidity', ...
        'Wedge01','Wedge02','Wedge03','Wedge04','Wedge05','Wedge06','Wedge07','Wedge08','Wedge09','Wedge10','Wedge11','Wedge12','Wedge13','Wedge14','Wedge15','Wedge16','Wedge17','Wedge18','Wedge19','Wedge20','Wedge21','Wedge22','Wedge23','Wedge24','Wedge25','Wedge26','Wedge27','Wedge28','Wedge29','Wedge30','Wedge31','Wedge32','Wedge33','Wedge34','Wedge35','Wedge36','Wedge37','Wedge38','Wedge39','Wedge40','Wedge41','Wedge42','Wedge43','Wedge44','Wedge45','Wedge46','Wedge47','Wedge48', ...
        'Ring01','Ring02','Ring03','Ring04','Ring05','Ring06','Ring07','Ring08','Ring09','Ring10','Ring11','Ring12','Ring13','Ring14','Ring15','Ring16','Ring17','Ring18','Ring19','Ring20','Ring21','Ring22','Ring23','Ring24','Ring25','Ring26','Ring27','Ring28','Ring29','Ring30','Ring31','Ring32','Ring33','Ring34','Ring35','Ring36','Ring37','Ring38','Ring39','Ring40','Ring41','Ring42','Ring43','Ring44','Ring45','Ring46','Ring47','Ring48','Ring49','Ring50', ...
        'HOG01','HOG02','HOG03','HOG04','HOG05','HOG06','HOG07','HOG08','HOG09','HOG10','HOG11','HOG12','HOG13','HOG14','HOG15','HOG16','HOG17','HOG18','HOG19','HOG20','HOG21','HOG22','HOG23','HOG24','HOG25','HOG26','HOG27','HOG28','HOG29','HOG30','HOG31','HOG32','HOG33','HOG34','HOG35','HOG36','HOG37','HOG38','HOG39','HOG40','HOG41','HOG42','HOG43','HOG44','HOG45','HOG46','HOG47','HOG48','HOG49','HOG50','HOG51','HOG52','HOG53','HOG54','HOG55','HOG56','HOG57','HOG58','HOG59','HOG60','HOG61','HOG62','HOG63','HOG64','HOG65','HOG66','HOG67','HOG68','HOG69','HOG70','HOG71','HOG72','HOG73','HOG74','HOG75','HOG76','HOG77','HOG78','HOG79','HOG80','HOG81', ...
        'Area_over_PerimeterSquared','Area_over_Perimeter','H90_over_Hflip','H90_over_H180','Hflip_over_H180','summedConvexPerimeter_over_Perimeter'};
%       feature_keys = {'PID', 'Area','numBlobs','MajorAxisLength','MinorAxisLength','Eccentricity','Orientation','ConvexHull','ConvexArea','EquivDiameter','Solidity','Extent','Perimeter','ConvexPerimeter','maxFeretDiameter','minFeretDiameter','BoundingBox_xwidth','BoundingBox_ywidth','texture_average_gray_level','texture_average_contrast','texture_smoothness','texture_third_moment','texture_uniformity','texture_entropy','moment_invariant1','moment_invariant2','moment_invariant3','moment_invariant4','moment_invariant5','moment_invariant6','moment_invariant7','shapehist_mean_normEqD','shapehist_median_normEqD','shapehist_skewness_normEqD','shapehist_kurtosis_normEqD','RWhalfpowerintegral','RWcenter2total_powerratio','Biovolume','SurfaceArea','RepresentativeWidth','summedArea','summedBiovolume','summedConvexArea','summedConvexPerimeter','summedMajorAxisLength','summedMinorAxisLength','summedPerimeter','summedSurfaceArea','H180','H90','Hflip','B180','B90','Bflip','RotatedBoundingBox_xwidth','RotatedBoundingBox_ywidth','rotated_BoundingBox_solidity',
%         'Wedge01','Wedge02','Wedge03','Wedge04','Wedge05','Wedge06','Wedge07','Wedge08','Wedge09','Wedge10','Wedge11','Wedge12','Wedge13','Wedge14','Wedge15','Wedge16','Wedge17','Wedge18','Wedge19','Wedge20','Wedge21','Wedge22','Wedge23','Wedge24','Wedge25','Wedge26','Wedge27','Wedge28','Wedge29','Wedge30','Wedge31','Wedge32','Wedge33','Wedge34','Wedge35','Wedge36','Wedge37','Wedge38','Wedge39','Wedge40','Wedge41','Wedge42','Wedge43','Wedge44','Wedge45','Wedge46','Wedge47','Wedge48',
%         'Ring01','Ring02','Ring03','Ring04','Ring05','Ring06','Ring07','Ring08','Ring09','Ring10','Ring11','Ring12','Ring13','Ring14','Ring15','Ring16','Ring17','Ring18','Ring19','Ring20','Ring21','Ring22','Ring23','Ring24','Ring25','Ring26','Ring27','Ring28','Ring29','Ring30','Ring31','Ring32','Ring33','Ring34','Ring35','Ring36','Ring37','Ring38','Ring39','Ring40','Ring41','Ring42','Ring43','Ring44','Ring45','Ring46','Ring47','Ring48','Ring49','Ring50',
%         'HOG01','HOG02','HOG03','HOG04','HOG05','HOG06','HOG07','HOG08','HOG09','HOG10','HOG11','HOG12','HOG13','HOG14','HOG15','HOG16','HOG17','HOG18','HOG19','HOG20','HOG21','HOG22','HOG23','HOG24','HOG25','HOG26','HOG27','HOG28','HOG29','HOG30','HOG31','HOG32','HOG33','HOG34','HOG35','HOG36','HOG37','HOG38','HOG39','HOG40','HOG41','HOG42','HOG43','HOG44','HOG45','HOG46','HOG47','HOG48','HOG49','HOG50','HOG51','HOG52','HOG53','HOG54','HOG55','HOG56','HOG57','HOG58','HOG59','HOG60','HOG61','HOG62','HOG63','HOG64','HOG65','HOG66','HOG67','HOG68','HOG69','HOG70','HOG71','HOG72','HOG73','HOG74','HOG75','HOG76','HOG77','HOG78','HOG79','HOG80','HOG81',
%         'Area_over_PerimeterSquared', 'Area_over_Perimeter', 'H90_over_Hflip', 'H90_over_H180', 'Hflip_over_H180', 'summedConvexPerimeter_over_Perimeter'};
  end
end
end

