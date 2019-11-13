function [hdr] = importHDR(filename)
%IMPORTHDR partially import hdr file
fid = fopen(filename);
f = textscan(fid,'%s','delimiter','\n'); 
fclose(fid);

if strcmp(f{1}{1}, 'softwareVersion: Imaging FlowCytobot Acquisition Software version 1.1.5.12');
  foo = strsplit(f{1}{117}, ':');
  if ~strcmp(foo{1}, 'runTime'); error('Unexpected value'); end
  hdr.runTime = str2double(foo{2});
  foo = strsplit(f{1}{118}, ':');
  if ~strcmp(foo{1}, 'inhibitTime'); error('Unexpected value'); end
  hdr.inhibitTime = str2double(foo{2});

  foo = strsplit(f{1}{46}, ':');
  if ~strcmp(foo{1}, 'PMTtriggerSelection_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTtriggerSelection_DAQ_MCConly = str2double(foo{2});

  foo = strsplit(f{1}{23}, ':');
  if ~strcmp(foo{1}, 'PMTAhighVoltage'); error('Unexpected value'); end
  hdr.PMTAhighVoltage = str2double(foo{2});
  foo = strsplit(f{1}{24}, ':');
  if ~strcmp(foo{1}, 'PMTBhighVoltage'); error('Unexpected value'); end
  hdr.PMTBhighVoltage = str2double(foo{2});

  foo = strsplit(f{1}{42}, ':');
  if ~strcmp(foo{1}, 'PMTAtriggerThreshold_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTAtriggerThreshold_DAQ_MCConly = str2double(foo{2});
  foo = strsplit(f{1}{43}, ':');
  if ~strcmp(foo{1}, 'PMTBtriggerThreshold_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTBtriggerThreshold_DAQ_MCConly = str2double(foo{2});
elseif strcmp(f{1}{1}, 'softwareVersion: Imaging FlowCytobot Acquisition Software version 1.1.5.19');
  foo = strsplit(f{1}{130}, ':');
  if ~strcmp(foo{1}, 'runTime'); error('Unexpected value'); end
  hdr.runTime = str2double(foo{2});
  foo = strsplit(f{1}{131}, ':');
  if ~strcmp(foo{1}, 'inhibitTime'); error('Unexpected value'); end
  hdr.inhibitTime = str2double(foo{2});

  foo = strsplit(f{1}{46}, ':');
  if ~strcmp(foo{1}, 'PMTtriggerSelection_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTtriggerSelection_DAQ_MCConly = str2double(foo{2});

  foo = strsplit(f{1}{23}, ':');
  if ~strcmp(foo{1}, 'PMTAhighVoltage'); error('Unexpected value'); end
  hdr.PMTAhighVoltage = str2double(foo{2});
  foo = strsplit(f{1}{24}, ':');
  if ~strcmp(foo{1}, 'PMTBhighVoltage'); error('Unexpected value'); end
  hdr.PMTBhighVoltage = str2double(foo{2});

  foo = strsplit(f{1}{42}, ':');
  if ~strcmp(foo{1}, 'PMTAtriggerThreshold_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTAtriggerThreshold_DAQ_MCConly = str2double(foo{2});
  foo = strsplit(f{1}{43}, ':');
  if ~strcmp(foo{1}, 'PMTBtriggerThreshold_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTBtriggerThreshold_DAQ_MCConly = str2double(foo{2});
else
  foo = strsplit(f{1}{98}, ':');
  if ~strcmp(foo{1}, 'runTime'); error('Unexpected value'); end
  hdr.runTime = str2double(foo{2});
  foo = strsplit(f{1}{99}, ':');
  if ~strcmp(foo{1}, 'inhibitTime'); error('Unexpected value'); end
  hdr.inhibitTime = str2double(foo{2});

  foo = strsplit(f{1}{46}, ':');
  if ~strcmp(foo{1}, 'PMTtriggerSelection_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTtriggerSelection_DAQ_MCConly = str2double(foo{2});

  foo = strsplit(f{1}{23}, ':');
  if ~strcmp(foo{1}, 'PMTAhighVoltage'); error('Unexpected value'); end
  hdr.PMTAhighVoltage = str2double(foo{2});
  foo = strsplit(f{1}{24}, ':');
  if ~strcmp(foo{1}, 'PMTBhighVoltage'); error('Unexpected value'); end
  hdr.PMTBhighVoltage = str2double(foo{2});

  foo = strsplit(f{1}{42}, ':');
  if ~strcmp(foo{1}, 'PMTAtriggerThreshold_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTAtriggerThreshold_DAQ_MCConly = str2double(foo{2});
  foo = strsplit(f{1}{43}, ':');
  if ~strcmp(foo{1}, 'PMTBtriggerThreshold_DAQ_MCConly'); error('Unexpected value'); end
  hdr.PMTBtriggerThreshold_DAQ_MCConly = str2double(foo{2});
end

end

