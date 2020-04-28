function export2PNGWithScaleBar( ROIfile_withpath, outputpath, ROInumbers, scale_bar )
%function [  ] = export_png_from_ROIlist( ROIfile_withpath, outputpath, ROInumbers )
%save png files to disk from ROI file, if no ROInumbers passed in, then all are exported
%Heidi M. Sosik, Woods Hole Oceanographic Institution, March 2014

% This function is edited by Nils with code from Pierre-Luc Grondin, May 2016
% add a scale bar at the bottom of each image

[basedir,filename] = fileparts(ROIfile_withpath);
%outputpath = [basedir filesep filename filesep];

%get ADC data for startbyte and length of each ROI
adcfile = [filename '.adc'];
adcdata = load([basedir filesep adcfile]);
% Skip empty files
if isempty(adcdata)
  fprintf('%s export_png EMPTY %s >>> SKIPPING \n', utcdate(now()), filename);
  return
end
% Parse adcdata
if isequal(filename(1), 'I')
    x = adcdata(:,12);  y = adcdata(:,13); startbyte = adcdata(:,14);
else  %new file format, case 'D*.roi'
    x = adcdata(:,16);  y = adcdata(:,17); startbyte = adcdata(:,18);
end;

% Create destination folder
if ~exist(outputpath, 'dir')
    mkdir(outputpath);
end;

% Make scale bar
% scale_bar.pixel_per_micron = 3.4;  % ratio
% scale_bar.height = 1.2;  % micron
% scale_bar.width = 10;  % micron
scale_bar_length_str = sprintf('%d %sm', scale_bar.width, char(956));
scale_bar_width = round(scale_bar.pixel_per_micron*scale_bar.width);
scale_bar_height = round(scale_bar.pixel_per_micron*scale_bar.height);
scale_bar_image = zeros(scale_bar_height,scale_bar_width);

if nargin < 3 || isempty(ROInumbers)
    [ROInumbers] = find(x>0);
end;
fid=fopen([ROIfile_withpath '.roi']);% '.roi']);
for count = 1:length(ROInumbers)
    num = ROInumbers(count);
    fseek(fid, startbyte(num), -1);
    img = fread(fid, x(num).*y(num), 'ubit8');
    img = reshape(img, x(num), y(num))';
    
    % Add scale bar
    img(size(img,1)-scale_bar_height-1:size(img,1)-2, 3:scale_bar_width+2) = scale_bar_image;
    img = insertText(img,[4 size(img,1)-scale_bar_height-15], scale_bar_length_str, 'BoxOpacity', 0.0, 'Fontsize', 8);

    pngname = sprintf('%s_%05d.png', filename, num);
%     if length(img) > 0
    if ~isempty(img)
        imwrite(uint8(img), fullfile(outputpath, pngname));
    end
end
fclose(fid);

end

