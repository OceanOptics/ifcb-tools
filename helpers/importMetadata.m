function [metadata] = importMetadata( path_metadata )
%IMPORTMETADATA import metadata.csv file
% Too filter a cell column use:
%   find(cellfun(@(x) ~isempty(x), m3.experiment_dilution))


f = fopen(path_metadata, 'r');
bin_metadata = textscan(f, '%s %f %f %f %f %d %s %s %s', 'Delimiter', ',', 'EmptyValue', NaN);
fclose(f);

id = bin_metadata{1};
dt = cellfun(@(x) datenum(x(2:16), 'yyyymmddTHHMMSS'), bin_metadata{1});
lat = bin_metadata{2};
lon = bin_metadata{3};
depth = bin_metadata{4};
concentration = bin_metadata{5};
flag = bin_metadata{6};
type = bin_metadata{7};
ref = bin_metadata{8};

% Load comments in table
stn_id = NaN(size(bin_metadata{1}));
cast_id = NaN(size(bin_metadata{1}));
source_id = NaN(size(bin_metadata{1}));
experiment_state = cell(size(bin_metadata{1}));
experiment_dilution = cell(size(bin_metadata{1}));
experiment_light_level = cell(size(bin_metadata{1}));
experiment_nutrients = cell(size(bin_metadata{1}));
experiment_bottle_id = cell(size(bin_metadata{1}));
culture_species = cell(size(bin_metadata{1}));
for i=1:size(bin_metadata{9},1)
  foo = strsplit(bin_metadata{9}{i}, ';');
  for bar=foo
    bar = strsplit(bar{1}, '=');
    if length(bar) == 2
      switch strtrim(bar{1})
        case 'stn_id'
          stn_id(i) = str2double(bar{2});
        case 'cast_id' 
          cast_id(i) = str2double(bar{2});
        case {'source_id', 'niskin_id'}
          source_id(i) = str2double(bar{2});
        % Experiments (PIC | Incubation)
        case {'T0/Tf', 't'}
          experiment_state{i} = bar{2};
        case {'dillution', 'dilution'}
          experiment_dilution{i} = bar{2};
        case 'light'
          experiment_light_level{i} = bar{2};
        case 'nutrients'
          experiment_nutrients{i} = bar{2};
        case 'bottle_id'
          experiment_bottle_id{i} = bar{2};
        case 'species'
          culture_species{i} = bar{2};
        case 'blank'
          ref{i} = ['blank ' bar{2}]; % Overwrite sample reference
        otherwise
          fprintf([id{i} ': Unknow parameter ' bar{1} '\n']);
      end
    end
  end
end

metadata = table(id, dt, lat, lon, depth, type, flag, concentration, ref,...
                 stn_id, cast_id, source_id,...
                 experiment_state, experiment_dilution,...
                 experiment_light_level, experiment_nutrients,...
                 experiment_bottle_id, culture_species);


end

% Mono Flag decoder
% switch bin_metadata{6}(i)
%   case 0
%     sample_flag = 'NA';
%   case 1
%     sample_flag = 'good';
%   case 2
%     sample_flag = 'incomplete';
%   case 4
%     sample_flag = 'bad';
%   case 8
%     sample_flag = 'questionnable';
%   case 16
%     sample_flag = 'scatter trigger';
%   case 32
%     sample_flag = 'flush';
%   otherwise
%     fprintf(['Unknow flag ' bin_id ' in metadata.csv\n']);
%     sample_flag = 'unknow';
% end;
