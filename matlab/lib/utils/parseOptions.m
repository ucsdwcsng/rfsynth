function [opts, unmatched] = parseOptions(opts, varargin)
% Argument parser convenience, returns unparsable arguments
% Example:
%
% function myfunc(varargin)
%     options = struct('Option1', 10, 'Option2', "default");
%     options, unmatched = parseOptions(options, varargin{:});
%     disp(options)
%     disp(unmatched)
% end
p = inputParser;
p.KeepUnmatched = 1;
fnames = fieldnames(opts);
for i = 1:length(fnames)
    addParameter(p, fnames{i}, opts.(fnames{i}));
end
parse(p, varargin{:});
opts = p.Results;
unmatched = structToVarargin(p.Unmatched);
end


function argout = structToVarargin(s)
% Get field names and values from the struct
fnames = fieldnames(s);
fvalues = struct2cell(s);

if isempty(fnames)
    argout = {};
    return
end

% Interleave field names and values
argout = cell(1, 2*numel(fnames));
argout(1:2:end) = fnames;
argout(2:2:end) = fvalues;
end