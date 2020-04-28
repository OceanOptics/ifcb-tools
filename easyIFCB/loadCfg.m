function cfg = loadCfg(filename)
% LOADCFG parse a .cfg file and returns a structure organized in section.
%
% INPUT:
%   filename <string> location of file to parse
%
% OUTPUT:
%   cfg <struct> containing parameters included in the file
%
% Based on:
%   init2struct.m by Andriy Nych 2014/02/01

f = fopen(filename,'r');                    % open file
while ~feof(f)                              % and read until it ends
    s = strtrim(fgetl(f));                  % remove leading/trailing spaces
    if isempty(s) || s(1)==';' || s(1)=='#' % skip empty & comments lines
        continue
    end
    if s(1)=='['                            % section header
        Section = genvarname(strtok(s(2:end), ']'));
        cfg.(Section) = [];              % create field
        continue
    end

    [Key,Val] = strtok(s, '=');             % Key = Value ; comment
    Val = strtrim(Val(2:end));              % remove spaces after =

    if isempty(Val) || Val(1)==';' || Val(1)=='#' % empty entry
        Val = [];
    elseif Val(1)=='"'                      % double-quoted string
        Val = strtok(Val, '"');
    elseif Val(1)==''''                     % single-quoted string
        Val = strtok(Val, '''');
    else
        Val = strtok(Val, ';');             % remove inline comment
        Val = strtok(Val, '#');             % remove inline comment
        Val = strtrim(Val);                 % remove spaces before comment

        [val, status] = str2num(Val);       %#ok<ST2NM>
        if status, Val = val; end           % convert string to number(s)
    end

    if ~exist('Section', 'var')             % No section found before
        cfg.(genvarname(Key)) = Val;
    else                                    % Section found before, fill it
        cfg.(Section).(genvarname(Key)) = Val;
    end

end
fclose(f);
end
