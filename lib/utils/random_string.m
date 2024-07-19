function randStr = random_string(prefixStr, n)
% A function that returns a random string of length n appended to a prefix.
%
% Args:
%   prefixStr (char): Prefix string.
%   n (int, optional): Number of random characters. Defaults to 8.
%
% Returns:
%   randStr (char): Random string appended to prefix (including prefix).

if nargin < 2
    n = 8; % default length
end

% Define the set of characters to choose from
charSet = ['a':'f', '0':'9'];

% Generate a random sequence of characters from the set
rIdx = randi(length(charSet), 1, n); % Generate random indices
randChars = string(charSet(rIdx)); % Select characters at random indices

% Append the random characters to the prefix
randStr = prefixStr + "_" + randChars;


end
