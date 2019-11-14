function [feature_data, feature_keys] = fastFeatureExtraction(path_to_bin, bin_name, min_feature_flag, parallel_flag)
% FASTFEATUREEXTRACTION will keep the blob extraction in memory and extract only relevant features
% without writing to disk the blob or the feature table which considerable accelerate the process.
% 
% Note that if parallel pool needs to be started at each execution of the function, it will be
% faster to run it on a single core

if nargin < 4; parallel_flag = false; end
if nargin < 3; min_feature_flag = false; end

if parallel_flag; parflag = Inf; else; parflag = 0; end

% Get images
targets = get_images_fromROI([path_to_bin filesep bin_name '.roi']);
n = length(targets.targetNumber);

% Update config
cfg = configure();
cfg.blob_props = {'Area', 'MajorAxisLength', 'MinorAxisLength', 'Perimeter',...
                  'ConvexHull', 'BoundingBox', 'ConvexArea', 'Orientation', 'Eccentricity','EquivDiameter'}; % Prop needed to compute other props
cfg.props2sum = {}; % Done directly below

% Init feature table
if min_feature_flag; feature_data = zeros(n,3, 'uint32');
else; feature_data = NaN(n, 14); end

parfor(i=1:n, parflag)
  % Configure Target
  target = {};
  target.config = cfg;
  target.image = targets.image{i};
  % Get Blob
  target = blob(target);
  if min_feature_flag
    % Output only features that come with blob extraction
    feature_data(i,:) = [targets.targetNumber(i), sum(target.blob_props.Area), target.blob_props.numBlobs];
  else
    % Get Features
    target = blob_geomprop(target);
    target = blob_texture(target);
    target = biovolume(target);
    summedArea = sum(target.blob_props.Area);
    equivDiameter = sqrt(4/pi * summedArea);
    feature_data(i,:) = [targets.targetNumber(i), summedArea, target.blob_props.numBlobs, equivDiameter, ...
                         sum([target.blob_props.FeretDiameter', target.blob_props.MinorAxisLength', target.blob_props.MajorAxisLength',...
                         target.blob_props.Perimeter', target.blob_props.Biovolume'],1), ...
                         target.blob_props.texture_average_contrast, target.blob_props.texture_average_gray_level,...
                         target.blob_props.texture_entropy, target.blob_props.texture_smoothness, target.blob_props.texture_uniformity];
  end
end

% Output features names
if nargout == 2
  if min_feature_flag
    feature_keys = ['PID', 'Area', 'NumberBlobs'];
  else
    feature_keys = ['PID', 'Area', 'NumberBlobs', 'EquivDiameter', 'FeretDiameter', 'MinorAxisLength', 'MajorAxisLength', 'Perimeter', 'Biovolume',...
                    'TextureContrast', 'TextureGrayLevel', 'TextureEntropy', 'TextureSmoothness', 'TextureUniformity'];
  end
end
end

