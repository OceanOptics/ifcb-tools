function [feature_data, feature_keys] = fastFeatureExtraction(path_to_bin, bin_name, min_feature_flag, parallel_flag)
% FASTFEATUREEXTRACTION will keep the blob extraction in memory and extract only relevant features
% without writing to disk the blob or the feature table which considerable accelerate the process.
%
% extract same features as features_slim, except keep only the summed features
% 
% Note that if parallel pool needs to be started at each execution of the function, it will be
% faster to run it on a single core

if nargin < 4; parallel_flag = false; end
if nargin < 3; min_feature_flag = false; end

if parallel_flag; parflag = Inf; else; parflag = 0; end

% Get images
targets = get_images_fromROI([path_to_bin filesep bin_name '.roi']);
n = length(targets.image);

% Update config
cfg = configure_test(); % updated for V4
cfg.blob_props = {'Area', 'BoundingBox', 'ConvexArea', 'Eccentricity', 'EquivDiameter', 'Extent', 'MajorAxisLength', ...
                  'MinorAxisLength', 'Orientation', 'Perimeter', 'Solidity'}; % updated with v4
cfg.props2sum = {}; % Done directly below

% Init feature table
if min_feature_flag; feature_data = zeros(n,3, 'uint32');
else; feature_data = NaN(n, 18); end

% Quick parfor acceleration
targets_image = targets.image;
targets_targetNumber = targets.targetNumber;

parfor(i=1:length(targets.image), parflag)
% for i=1:length(targets.image)
  % Configure Target
  target = {};
  target.config = cfg;
  target.image = targets_image{i};
  % Get Blob
  target = blob_v4(target); % Updated for V4
  if min_feature_flag
    % Output only features that come with blob extraction
    feature_data(i,:) = [targets_targetNumber(i), sum(target.blob_props.Area), target.blob_props.numBlobs];
  else
    % Get Features
    target = blob_geomprop(target);
    target = blob_rotate(target);    % Added on v4
%     target = blob_texture(target); % Removed on v4
    target = biovolume(target);
    summedArea = sum(target.blob_props.Area);
    summedEquivDiameter = sqrt(4/pi * summedArea);
    feature_data(i,:) = [targets.targetNumber(i), summedArea, target.blob_props.numBlobs, summedEquivDiameter, ...
                         sum([target.blob_props.minFeretDiameter', target.blob_props.maxFeretDiameter',...
                         target.blob_props.MinorAxisLength', target.blob_props.MajorAxisLength',...
                         target.blob_props.Perimeter', target.blob_props.Biovolume',... 
                         target.blob_props.ConvexArea', target.blob_props.ConvexPerimeter',...
                         target.blob_props.SurfaceArea'],1),...
                         target.blob_props.Eccentricity(1), target.blob_props.Extent(1),...
                         target.blob_props.Orientation(1), target.blob_props.RepresentativeWidth(1),...
                         target.blob_props.Solidity(1)];
  end
end

% Output features names
if nargout == 2
  if min_feature_flag
    feature_keys = {'PID', 'Area', 'NumberBlobs'};
  else
    feature_keys = {'PID', 'Area', 'NumberBlobs', 'EquivDiameter', 'MinFeretDiameter', 'MaxFeretDiameter', 'MinorAxisLength', 'MajorAxisLength', 'Perimeter', 'Biovolume',...
                    'ConvexArea', 'ConvexPerimeter', 'SurfaceArea', 'Eccentricity', 'Extent', 'Orientation', 'RepresentativeWidth', 'Solidity'};
  end
end
end

