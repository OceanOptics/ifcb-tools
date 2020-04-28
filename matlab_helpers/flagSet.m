function [num] = flagSet(str)
%FLAGSET convert flag from list of string to int32 for efficient storage
%   each bit assigned is used as a flag
%   List of flags available:
%     - 0    No flag
%     - 2^0  Good <default>
%     - 2^1  Aborted | Incomplete (quantification can be biased)
%     - 2^2  Bad | Ignore | Delete | Failed | Bubbles
%     - 2^3  Questionnable
%     - 2^4  customTrigger  (Trigger mode different than PMTB)
%     - 2^5  Flush
%     - 2^6  customVolume: Volume sampled different than 5 mL
%     - 2^7  badAlignment (can underestimate concentration)
%     - 2^8  badFocus (area of particles is affected)
%     - 2^9  timeOffset (time of IFCB is incorrect)
%     - 2^10 Corrupted (good sample, bad file)

  if isempty(strtrim(str)) % good
    num = int32(1);
  elseif strcmp(strtrim(str), 'unknown')
    num = int32(0);
  else
    num = int32(0);
    for str_flag = strtrim(strsplit(str, ';'))
      switch lower(str_flag{1})
        case 'corrupted'
          num = bitset(num, 10+1);
        case {'timeoffset', 'time_offset'}
          num = bitset(num, 9+1);
        case {'bfocus', 'badfocus', 'bad_focus'}
          num = bitset(num, 8+1);
        case {'balignment', 'badalignment', 'bad_alignment'}
          num = bitset(num, 7+1);
        case {'cvolume', 'customvolume', 'custom_volume'}
          num = bitset(num, 6+1);
        case 'flush'
          num = bitset(num, 5+1);
        case {'ctrigger', 'customtrigger', 'custom_trigger', 'scatter trigger'}
          num = bitset(num, 4+1);
        case 'questionnable'
          num = bitset(num, 3+1);
        case {'bad', 'ignore', 'delete', 'failed', 'bubble', 'bubbles'}
          num = bitset(num, 2+1);
        case {'incomplete', 'aborted'}
          num = bitset(num, 1+1);
        otherwise
          if ~isempty(str_flag{1});
            error('Unknown flag: %s', str_flag{1});
          end
      end
    end
  end
end

