function [ sel ] = getSelection( bin, filename )
%GETSELECTION Import selection from list in text file
if nargin > 1 && ~isempty(filename) && ~strcmp(filename(end-2:end),'all')
  % load selection from file
  f = fopen(filename);
  data = textscan(f, '%s', 'Delimiter', ',');
  fclose(f);
  sel = NaN(size(data{1})); j = 1;
  for i = 1:size(bin,1)
    if any(strcmp(data{1}, bin{i}));  sel(j,1) = i;  j = j + 1; end;
  end;
  sel(isnan(sel)) = [];
else
  % select all bin as no file is specified
  sel = [1:size(bin,1)]';
end;
end

