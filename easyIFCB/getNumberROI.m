function n = getNumberROI(adc_filename)
% Get number of ROI
adc=load(adc_filename);
% x = adc(:,12);  y = adc(:,13); startbyte = adc(:,14);
% x = adc(:,16);  y = adc(:,17); startbyte = adc(:,18);
n=size(adc,1);
end