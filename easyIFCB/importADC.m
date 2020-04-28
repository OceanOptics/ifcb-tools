function adc = importADC(filename)


% Build data parser
parser = [repmat('%f',1,24) '%[^\n\r]'];

% Parse data
fid = fopen(filename);
adc = textscan(fid, parser, 'Delimiter', ',');
% dt = t{1};
% c = [t{i_c}];
% a = [t{i_a}];
fclose(fid);
% Make table
adc = array2table([adc{1:24}]);
adc.Properties.VariableNames = {'itrigger', 'ADC_time', 'PMTA', 'PMTB', 'PMTC', 'PMTD', 'peakA', 'peakB', 'peakC', 'peakD', 'timeOfFlight', 'grabTimeStart', 'grabTimeEnd', 'ROIx', 'ROIy', 'ROIwidth', 'ROIheight', 'start_byte', 'comparator_out', 'StartPoint', 'SignalLength', 'status', 'runTime', 'inhibitTime'};
end