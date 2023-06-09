function [str] = flagGet(num)
%FLAGGET convert flag from int32 to list of string easy to read
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
%
% Input num should be int32

  str = '';
  for i=find(bitget(num, 1:11))-1
    switch i
      case 0
        str = [str '; good'];
      case 1
        str = [str '; aborted'];
      case 2
        str = [str '; bad'];
      case 3
        str = [str '; questionnable'];
      case 4
        str = [str '; customTrigger'];
      case 5
        str = [str '; flush'];
      case 6
        str = [str '; customVolume'];
      case 7
        str = [str '; badAlignment'];
      case 8
        str = [str '; badFocus'];
      case 9
        str = [str '; timeOffset'];
      case 10
        str = [str '; corrupted'];
      case 11
        str = [str '; delayRun'];
      otherwise
        error('Unknown flag: %d', i);
    end
  end
  if isempty(str)
    str = 'NA'; % no flag available
  else
    str = str(3:end);
  end
end

