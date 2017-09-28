function buildEcoTaxaTSV(dir_features, dir_adc, bin_ids, dir_out, path_metadata, global_metadata, par_flag)
% buildEcoTaxaTSV build tsv file for EcoTaxa
%   one tsv file is built by bin

% Load metadata.csv
%   1 bin identification number <D<YYYYMMDD>T<hhmmss>_IFCB<###>>
%   2 latitude <double> (decimal degree)
%   3 longitude <double> (decimal degree)
%   4 depth <double> (meters)
%   5 concentration factor <double> (no units)
%   6 flag <int32> (0:NaN, 1:good, 2:partial sample (not valid for quantification), 4:bad sample)
%   7 sample type <string> (e.g. inline, niskin, or experiment)
%   8 sample id <string> (CTD cast identification number)
%   9 comments <string>
f = fopen(path_metadata, 'r');
bin_metadata = textscan(f, '%s %f %f %f %f %d %s %s %s', 'Delimiter', ',', 'EmptyValue', NaN);
fclose(f);

% Load features names for header
f = fopen([dir_features bin_ids{1} '_fea_v2.csv'], 'r');
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

% Load ADC names for header
adc_headers = {'pmt_scattering'; 'pmt_fluorescence'; 'peak_scattering'; 'peak_fluorescence'};
adc_sel = [3,4,7,8];

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
  {'sample_id', '[t]'}, {'sample_source', '[t]'}, {'sample_flag', '[t]'},... % NAAMES 3 Specific from here
  {'sample_cruise', '[t]'}, {'sample_vessel', '[t]'}, {'sample_reference', '[t]'},...
  {'sample_station', '[t]'}, {'sample_cast', '[f]'}, {'sample_source_id', '[t]'},...
  {'sample_experiment_state', '[t]'}, {'sample_experiment_dilution', '[t]'},...
  {'sample_experiment_light_level', '[t]'}, {'sample_experiment_nutrients', '[t]'},...
  {'sample_culture_species', '[t]'}};
%   {'sample_id', '[t]'}, {'sample_source', '[t]'}, {'sample_flag', '[t]'},... % PEACETIME Specific from here
%   {'sample_cruise', '[t]'}, {'sample_vessel', '[t]'}, {'sample_reference', '[t]'},...
%   {'sample_station', '[t]'}, {'sample_cast', '[f]'}, {'sample_source_id', '[t]'}};
  % NAAMES 1 & 2 Specific
%   {'sample_id', '[t]'}, {'sample_type', '[t]'}, {'sample_flag', '[t]'},...
%   {'sample_cruise', '[t]'}, {'sample_vessel', '[t]'}, {'sample_profile_id', '[t]'},...
%   {'sample_station', '[f]'}, {'sample_cast', '[f]'}, {'sample_niskin', '[f]'},...
%   {'sample_concentration', '[f]'}, {'sample_experiment_dilution', '[f]'},...
%   {'sample_experiment_state', '[t]'}, {'sample_experiment_bottle', '[t]'}};
  % Not needed (no classification done at first)
  % {'object_annotation_date', '[t]'}, {'object_annotation_time', '[t]'},...
  % {'object_annotation_category', '[t]'}, {'object_annotation_person_name', '[t]'},...
  % {'object_annotation_person_email', '[t]'}, {'object_annotation_status', '[t]'},...
header_name = [cell2mat(cellfun(@(x) [x{1} '\t'], meta_headers, 'uni', false)) ...
               cell2mat(cellfun(@(x) ['object_' x '\t'], ftr_headers, 'uni', false)') ...
               cell2mat(cellfun(@(x) ['object_' x '\t'], adc_headers, 'uni', false)')];
header_name = header_name(1:end-2);
header_type = [cell2mat(cellfun(@(x) [x{2} '\t'], meta_headers, 'uni', false)) ...
               repmat('[f]\t',1,size(ftr_headers,1)) ...
               repmat('[f]\t',1,size(adc_headers,1))];
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
% bin_ids = cellfun(@(c)c(1:end-11),feature_ids,'uni',false);

% Check parallel flag
if ~exist('par_flag', 'var'); par_flag = false; end;
if par_flag; parfor_arg = Inf;
else; parfor_arg = 0; end;

% Loop through each bin
for i_bin=1:size(bin_ids,1)
% parfor (i_bin=1:size(feature_ids,1), parfor_arg)
  % Get ids
  feature_id = [bin_ids{i_bin} '_fea_v2.csv'];
  adc_id = [bin_ids{i_bin} '.adc'];
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
    fprintf('Loading %s\n', feature_id);
    ftr = dlmread([dir_features feature_id], ',', 1, 0);
  else
    fprintf('%s build_tsv EMPTY FEATURES %s >>> SKIPPING \n', utcdate(now()), bin_id);
    continue;
  end
  
  % Load adc
  % WARNING: USe ROI# to be in sync with features
  %      ex: adc(ftr(i,1),j); % i = ROI#, j = feature
  foo = [dir_adc adc_id];
  if exist(foo, 'file')
    % Check if file is not empty
    s = dir(foo);
    if s.bytes ~= 0
      fprintf('Loading %s\n', adc_id);
      adc = dlmread(foo, ',');
    else
      fprintf('%s build_tsv EMPTY ADC %s >>> SKIPPING \n', utcdate(now()), bin_id);
      continue;
    end
  else
    fprintf('%s build_tsv NO ADC %s >>> SKIPPING \n', utcdate(now()), bin_id);
    continue;
  end
  
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
%   sample_type = bin_metadata{7}{i_bm};
  sample_source = bin_metadata{7}{i_bm};
%   sample_flag = '';
  switch bin_metadata{6}(i_bm)
    case 0
      sample_flag = 'NA';
    case 1
      sample_flag = 'good';
    case 2
      sample_flag = 'incomplete';
    case 4
      sample_flag = 'bad';
    case 8
      sample_flag = 'questionnable';
    case 16
      sample_flag = 'scatter trigger';
    case 32
      sample_flag = 'flush';
    otherwise
      fprintf(['Unknow flag ' bin_id ' in metadata.csv\n']);
      sample_flag = 'unknow';
  end;
%   sample_profile_id = bin_metadata{8}{i_bm};
  sample_reference = bin_metadata{8}{i_bm};
  sample_station = '';
  sample_cast = '';
%   sample_niskin = '';
  sample_source_id = '';
%   if ~isnan(bin_metadata{5}(i_bm)); sample_concentration = num2str(bin_metadata{5}(i_bm)); else sample_concentration = ''; end;
  sample_experiment_state = '';
  sample_experiment_dilution = '';
  sample_experiment_light_level = '';
  sample_experiment_nutrients = '';
%   sample_experiment_bottle = '';
  sample_culture_species = '';
  
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
        case 'source_id'
          sample_source_id = bar{2};
%         case 'niskin_id'
%           sample_niskin = bar{2};
        % Experiments (PIC | Incubation)
        case {'T0/Tf', 't'}
          sample_experiment_state = bar{2};
        case {'dillution', 'dilution'}
          sample_experiment_dilution = bar{2};
        case 'light'
          sample_experiment_light_level = bar{2};
        case 'nutrients'
          sample_experiment_nutrients = bar{2};
        case 'species'
          sample_culture_species = bar{2};
%         case 'bottle_id'
%           sample_experiment_bottle = bar{2};
        otherwise
          fprintf(['Unknow comment ' bar{1} ' in ' bin_id ' in metadata.csv\n']);
      end
    end
  end
  
  % Set Sample ID
  sample_id = '';
%   switch sample_type
  switch sample_source
    case 'inline'
%       DEPRECATED
%       if strcmp(global_metadata.process.selection_name, 'All')
%         sample_id = [global_metadata.meta.cruise_id '_INLINE_' bin_id];
%       else
%         sample_id = [global_metadata.meta.cruise_id '_INLINE_' global_metadata.process.selection_name '_' bin_id];
%       end;
      if isempty(sample_station)
        sample_id = [global_metadata.meta.cruise_id '_INLINE_' bin_id];
      else
        sample_id = [global_metadata.meta.cruise_id '_INLINE_' sample_station '_' bin_id];
      end
    case 'niskin'
%       sample_id = [sample_profile_id '_NISKIN_' sample_niskin '_' bin_id];
      sample_id = [sample_reference '_NISKIN_' sample_source_id '_' bin_id];
    case 'incubation'
      sample_id = [sample_reference '_INCUBATION_' bin_id];
    case 'micro-layer'
      sample_id = [global_metadata.meta.cruise_id 'S' sample_station 'MLC'  sample_cast '_MICRO-LAYER_' bin_id];
    case 'PIC'
      sample_id = [global_metadata.meta.cruise_id '_PIC_' sample_reference '_' bin_id];
    case 'culture'
      sample_id = ['CULTURE_' sample_culture_species '_' bin_id];
    case 'minicosm'
      sample_id = ['MINICOSM_' sample_station '_' sample_reference '_' sample_source_id '_' bin_id];
    case 'test'
      sample_id = ['TEST_' bin_id];
    case 'mooring'
      sample_id = [sample_reference '_MOORING_' bin_id];
    otherwise
      fprintf(['Unknow sample_source ' bin_id ' in metadata.csv\n']);
  end

  % Open TSV file
  f = fopen([dir_out 'ecotaxa_' bin_id '.tsv'], 'w');

  % Write TSV file header
  fprintf(f, header);
  
  % Loop through all roi of bin
  for i=1:size(ftr,1)
    object_id = sprintf('%s_%05d', bin_id, ftr(i,1));
    img_file_name = [object_id '.png'];
    
    % Write metadata
    fprintf(f, '%s\t', img_file_name, object_id, object_link, object_lat, object_lon,...
              object_date, object_time, object_depth_min, object_depth_max,...
              acq_id, acq_instrument, num2str(acq_resolution_pixel_to_micron),...
              process_id, process_soft, process_soft_version,...
              process_script, process_script_version,...
              process_library, process_library_version,...
              process_date, process_time,...
              sample_id, sample_source, sample_flag,...% NAAMES 3 Specific
              sample_cruise, sample_vessel, sample_reference,...
              sample_station, sample_cast, sample_source_id,...
              sample_experiment_state, sample_experiment_dilution,...
              sample_experiment_light_level, sample_experiment_nutrients,...
              sample_culture_species);
%               sample_id, sample_source, sample_flag,...% PEACETIME Specific
%               sample_cruise, sample_vessel, sample_reference,...
%               sample_station, sample_cast, sample_source_id);
              % NAAMES 1 & 2 Specific
%               sample_id, sample_type, sample_flag,...
%               sample_cruise, sample_vessel, sample_profile_id,...
%               sample_station, sample_cast, sample_niskin,...
%               sample_concentration, sample_experiment_dilution,...
%               sample_experiment_state, sample_experiment_bottle);

    % Write features
    for j=1:size(ftr,2)%-1
      fprintf(f, '%s\t', num2str(ftr(i, j)));
    end
%     fprintf(f, '%s\n', num2str(ftr(i, size(ftr,2))));
    
    % Write ADC
    % Load adc
    % WARNING: Indexing of ADC is based on ROI# to be in sync with features
    %      ex: adc(ftr(i,1),j); % i = ROI#, j = feature
    for j=1:size(adc_sel,2)-1
      fprintf(f, '%s\t', num2str(adc(ftr(i,1), adc_sel(j))));
    end
    fprintf(f, '%s\n', num2str(adc(ftr(i,1), adc_sel(size(adc_sel,2)))));
  end

  % Close TSV file
  fclose(f);
  if ~par_flag; fprintf('DONE\n'); end
  end
end

end