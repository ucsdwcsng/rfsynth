function write_cf32_file(pathIn, samplesIQ)
fid = fopen(pathIn, 'w');
assert(fid >= 0, 'write_cf32_file:OpenFailed', 'Unable to open %s for writing.', pathIn);
cleanup = onCleanup(@() fclose(fid));

interleaved = zeros(2 * numel(samplesIQ), 1, 'single');
interleaved(1:2:end) = single(real(samplesIQ));
interleaved(2:2:end) = single(imag(samplesIQ));
fwrite(fid, interleaved, 'single');
