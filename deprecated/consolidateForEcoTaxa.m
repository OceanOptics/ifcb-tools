function consolidateForEcoTaxa(dir_image, dir_tsv, bins, dir_out, zip_flag, rm_tmp_flag, par_flag)
% CONSOLIDATEFORECOTAXA consolidate images and ecotaxa_*.tsv file in one
% folder and compress them if necessary

if nargin < 5; zip_flag = false; end
if nargin < 6; rm_tmp_flag = false; end
if nargin < 7; par_flag = false; end

% Check parallel flag
if par_flag; parfor_arg = Inf;
else; parfor_arg = 0; end;

% Loop through each bin
update_flag=zeros(size(bins));
parfor (i=1:size(bins,1), parfor_arg)
% for i=1:size(bins,1)
  bin = bins{i};
  dir_bin=[dir_out bin filesep];
  
  if ~isdir(dir_bin)
    fprintf('%s conslidate_for_EcoTaxa PREPARING %s\n', utcdate(now()), bin);
  
    % Set flags
    missing_images = false;
    missing_tsv = false;
    
    % Copy/Move images
    path_images = [dir_image bin];
    if isdir(path_images)
      if ~isempty(dir([path_images filesep '*.png']))
        if rm_tmp_flag; movefile(path_images, dir_out);
        else; copyfile(path_images, dir_bin); end
      else
%         rmdir(path_images); % Remove empty directory
        missing_images = true;
      end
    else
      missing_images = true;
    end

    % Copy/Move features
    path_tsv = [dir_tsv 'ecotaxa_' bin '.tsv'];
    if ~exist(path_tsv, 'file')
      missing_tsv = true;
    end
    if ~missing_tsv && ~missing_images
      if rm_tmp_flag; movefile(path_tsv, dir_bin);
      else; copyfile(path_tsv, dir_bin); end
    end
    
    % Check any missing file
    if missing_images && missing_tsv
      fprintf('%s consolidate_for_EcoTaxa EMPTY %s >>> SKIPPING \n', utcdate(now()), bin);
    elseif missing_images
      fprintf('ERROR: MISSING Images: %s\n', [dir_tsv bin '.tsv']);
    elseif missing_tsv
      fprintf('ERROR: MISSING EcoTaxa TSV: %s\n', [dir_tsv bin '.tsv']);
    end

    % Data was updates need to (re)-zip data
    update_flag(i) = 1;
  else
    fprintf('%s conslidate_for_EcoTaxa SKIPPING %s\n', utcdate(now()), bin);
  end
end

if zip_flag
  % Zip
  fprintf('%s conslidate_for_EcoTaxa ZIPPING ... ', utcdate(now()));
  path_zip = [dir_out(1:end-1) '.zip'];
  if ~exist(path_zip, 'file') || any(update_flag)
    zip([dir_out(1:end-1) '.zip'], dir_out);
  end
  fprintf('Done\n');
  if rm_tmp_flag; rmdir(dir_out); end;
end

end