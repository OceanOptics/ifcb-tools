function buildEcoTaxaTSV(dir_features, feature_ids, dir_out, path_metadata, global_metadata, par_flag)
% buildEcoTaxaTSV build tsv file for EcoTaxa
%   one tsv file is built by bin

% Load metadata.csv
%   1 bin identification number <D<YYYYMMDD>T<hhmmss>_IFCB<###>>
%   2 latitude <double> (decimal degree)
%   3 longitude <double> (decimal degree)
%   4 depth <double> (meters)
%   5 concentration factor <double> (no units)
%   6 flag <int32> (0:NaN, 1:good, 2:partial sample (not valid for quantification), 4:bad sample)
%   7 sample type <string> (inline, niskin, or incubation)
%   8 sample id <string> (CTD cast identification number)
%   9 comments <string>
f = fopen(path_metadata, 'r');
bin_metadata = textscan(f, '%s %f %f %f %f %d %s %s %s', 'Delimiter', ',', 'EmptyValue', NaN);
fclose(f);

% Load features names for header
f = fopen([dir_features feature_ids{1}], 'r');
ftr_headers = textscan(f, '%s', 1);
fclose(f);
ftr_headers = strsplit(ftr_headers{1}{1}, ',')';
% Reformat names (lower case with underscore)
for i=1:size(ftr_headers,1)
  % lowercase first caractere
  foo = regexprep(ftr_headers{i},'^.','${lower($0)}');
  % lowercase letter series of uppercase before number
  foo = regexprep(foo,'([A-Z]+[0-9])|([_][A-Z])','${[lower($0)]}');
  % lowercase other uppercase caracter and insert an underscore
  ftr_headers{i} = regexprep(foo,'(([a-z][A-Z]+)|([A-Z]+[a-z]))','${[lower($0(1)) ''_'' lower($0(2))]}');
end

% Set header
meta_headers = {{'img_file_name', '[t]'},... % 'img_rank', '[f]'},...
  {'object_id', '[t]'}, {'object_link', '[t]'},...
  {'object_lat', '[f]'}, {'object_lon', '[f]'},...
  {'object_date', '[t]'}, {'object_time', '[t]'},...
  {'object_depth_min', '[f]'}, {'object_depth_max', '[f]'},...
  {'acq_id', '[t]'}, {'acq_instrument', '[t]'},...
  {'acq_resolution_pixels_per_micron', '[f]'},...
  {'process_id', '[t]'}, {'process_soft', '[t]'}, {'process_soft_version', '[t]'},...
  {'process_script', '[t]'}, {'process_script_version', '[t]'},...
  {'process_library', '[t]'}, {'process_library_version', '[t]'},...
  {'process_date', '[t]'}, {'process_time', '[t]'},...
  {'sample_id', '[t]'}, {'sample_type', '[t]'}, {'sample_flag', '[t]'},...
  {'sample_cruise', '[t]'}, {'sample_vessel', '[t]'}, {'sample_profile_id', '[t]'},...
  {'sample_station', '[f]'}, {'sample_cast', '[f]'}, {'sample_niskin', '[f]'},...
  {'sample_concentration', '[f]'}, {'sample_experiment_dilution', '[f]'},...
  {'sample_experiment_state', '[t]'}, {'sample_experiment_bottle', '[t]'}};
  % {'object_annotation_date', '[t]'}, {'object_annotation_time', '[t]'},...
  % {'object_annotation_category', '[t]'}, {'object_annotation_person_name', '[t]'},...
  % {'object_annotation_person_email', '[t]'}, {'object_annotation_status', '[t]'},...
header_name = [cell2mat(cellfun(@(x) [x{1} '\t'], meta_headers, 'uni', false)) ...
               cell2mat(cellfun(@(x) ['object_' x '\t'], ftr_headers, 'uni', false)')];
header_name = header_name(1:end-2);
header_type = [cell2mat(cellfun(@(x) [x{2} '\t'], meta_headers, 'uni', false)) ...
               repmat('[f]\t',1,size(ftr_headers,1))];
header_type = header_type(1:end-2);
header = [header_name '\n' header_type '\n'];

% Prepare metadata for each roi
object_link = global_metadata.meta.website;
acq_id = global_metadata.meta.instrument;
acq_instrument = 'IFCB';
acq_resolution_pixel_to_micron = global_metadata.meta.resolution_pixel_per_micron;
process_id = global_metadata.process.id;
process_soft = global_metadata.process.soft;
process_soft_version = global_metadata.process.soft_version;
process_script = global_metadata.process.script;
process_script_version = global_metadata.process.script_version;
process_library = global_metadata.process.library;
process_library_version = global_metadata.process.library_version;
process_date = global_metadata.process.date;
process_time = global_metadata.process.time;
sample_cruise = global_metadata.meta.cruise;
sample_vessel = global_metadata.meta.vessel;
% Loop throught all bins given
bin_ids = cellfun(@(c)c(1:end-11),feature_ids,'uni',false);

% Check parallel flag
if ~exist('par_flag', 'var'); par_flag = false; end;
if par_flag; parfor_arg = Inf;
else; parfor_arg = 0; end;

% Loop through each bin
parfor (i_bin=1:size(feature_ids,1), parfor_arg)
  % Get ids
  feature_id = feature_ids{i_bin};
  bin_id = bin_ids{i_bin};
  filename_out = [dir_out 'ecotaxa_' bin_id '.tsv'];
  if exist(filename_out, 'file')
    fprintf('%s build_tsv SKIPPING %s\n', utcdate(now()), bin_id);
  else
    if par_flag
      fprintf('%s build_tsv BUILDING %s ...\n', utcdate(now()), bin_id);
    else
      fprintf('%s build_tsv BUILDING %s ... ', utcdate(now()), bin_id);
    end;
  % Get index in metadata of current bin  
  i_bm = find(strcmp(bin_metadata{1}, bin_id));
  
  % Load features
  if exist([dir_features feature_id], 'file');
    ftr = dlmread([dir_features feature_id], ',', 1, 0);
  else
    fprintf('%s build_tsv EMPTY %s >>> SKIPPING \n', utcdate(now()), bin_id);
    continue;
  end;
  
  % Prepare bin's metadata
  object_lat = num2str(bin_metadata{2}(i_bm));
  object_lon = num2str(bin_metadata{3}(i_bm));
  object_date = bin_id(2:9);
  object_time = bin_id(11:16);
  if ~isnan(bin_metadata{4}(i_bm))
    object_depth_min = num2str(bin_metadata{4}(i_bm));
    object_depth_max = num2str(bin_metadata{4}(i_bm));
  else
    object_depth_min = '';
    object_depth_max = '';
  end;
  sample_type = bin_metadata{7}{i_bm};
  sample_flag = '';
  switch bin_metadata{6}(i_bm)
    case 0
      sample_flag = 'unknow';
    case 1
      sample_flag = 'good';
    case 2
      sample_flag = 'incomplete sample';
    case 4
      sample_flag = 'bad';
    otherwise
      fprintf(['Unknow flag ' bin_id ' in metadata.csv\n']);
      sample_flag = 'unknow';
  end;
  sample_profile_id = bin_metadata{8}{i_bm};
  sample_station = '';
  sample_cast = '';
  sample_niskin = '';
  if ~isnan(bin_metadata{5}(i_bm)); sample_concentration = num2str(bin_metadata{5}(i_bm)); else sample_concentration = ''; end;
  sample_experiment_state = '';
  sample_experiment_dilution = '';
  sample_experiment_bottle = '';
  
  % Load comments in metadata
  foo = strsplit(bin_metadata{9}{i_bm}, ';');
  for bar=foo
    bar = strsplit(bar{1}, '=');
    if length(bar) == 2
      switch strtrim(bar{1})
        case 'stn_id'
          sample_station = bar{2};
        case 'cast_id' 
          sample_cast = bar{2};
        case 'niskin_id'
          sample_niskin = bar{2};
        case 'T0/Tf'
          sample_experiment_state = bar{2};
        case 'dillution'
          sample_experiment_dilution = bar{2};
        case 'bottle_id'
          sample_experiment_bottle = bar{2};
        otherwise
          fprintf(['Unknow comment ' bar{1} ' in ' bin_id ' in metadata.csv\n']);
      end;
    end;
  end;
  
  % Set Sample ID
  sample_id = '';
  switch sample_type
    case 'inline'
      if strcmp(global_metadata.process.selection_name, 'All')
        sample_id = [global_metadata.meta.cruise_id '_INLINE_' object_id];
      else
        sample_id = [global_metadata.meta.cruise_id '_INLINE_' global_metadata.process.selection_name '_' object_id];
      end;
    case 'niskin'
      sample_id = [sample_profile_id '_NISKIN_' sample_niskin '_' object_id];
    case 'incubation'
      sample_id = [sample_profile_id '_EXPERIMENT_' sample_experiment_bottle '_' object_id];
    otherwise
      fprintf(['Unknow sample_type ' bin_id ' in metadata.csv\n']);
  end

  % Open TSV file
  f = fopen([dir_out 'ecotaxa_' bin_id '.tsv'], 'w');

  % Write TSV file header
  fprintf(f, header);
  
  % Loop through all roi of bin
  for i=1:size(ftr,1)
    object_id = sprintf('%s_%05d', bin_id, ftr(i,1));
    img_file_name = [object_id '.png'];
    
    % Set meta data
    fprintf(f, '%s\t', img_file_name, object_id, object_link, object_lat, object_lon,...
              object_date, object_time, object_depth_min, object_depth_max,...
              acq_id, acq_instrument, num2str(acq_resolution_pixel_to_micron),...
              process_id, process_soft, process_soft_version,...
              process_script, process_script_version,...
              process_library, process_library_version,...
              process_date, process_time,...
              sample_id, sample_type, sample_flag,...
              sample_cruise, sample_vessel, sample_profile_id,...
              sample_station, sample_cast, sample_niskin,...
              sample_concentration, sample_experiment_dilution,...
              sample_experiment_state, sample_experiment_bottle);
    % Set feature data
    for j=1:size(ftr,2)-1
      fprintf(f, '%s\t', num2str(ftr(i, j)));
    end;
    % Write line of feature
    fprintf(f, '%s\n', num2str(ftr(i, size(ftr,2))));
  end;

  % Close TSV file
  fclose(f);
  if ~par_flag; fprintf('DONE\n'); end;
  end;
end

end