function [tx_vec_air, params] = ofdm_tx_from_test_vector(params, payload)
data_symbols = payload.data_symbols;
pilot_symbols = payload.pilot_symbols;

params.N_OFDM_SYMS = size(data_symbols, 2);
params.N_DATA_SYMS = numel(data_symbols);

if size(data_symbols, 1) ~= numel(params.SC_IND_DATA)
    error('ofdm_tx_from_test_vector:InvalidDataShape', ...
        'Expected %d data carriers, got %d.', ...
        numel(params.SC_IND_DATA), size(data_symbols, 1));
end

if size(pilot_symbols, 1) ~= numel(params.SC_IND_PILOTS)
    error('ofdm_tx_from_test_vector:InvalidPilotShape', ...
        'Expected %d pilot carriers, got %d.', ...
        numel(params.SC_IND_PILOTS), size(pilot_symbols, 1));
end

if size(pilot_symbols, 2) ~= params.N_OFDM_SYMS
    error('ofdm_tx_from_test_vector:InvalidPilotCount', ...
        'Pilot matrix must have %d OFDM symbols, got %d.', ...
        params.N_OFDM_SYMS, size(pilot_symbols, 2));
end

sts_t = params.sts_t;
lts_t = params.lts_t;

if isfield(params, 'config_5g')
    init_cp = params.config_5g.init_cp;
    preamble1 = [lts_t((params.N_SC - init_cp + 1):params.N_SC) lts_t];
    preamble2 = [lts_t((params.N_SC - params.CP_LEN + 1):params.N_SC) lts_t];
    preamble = [preamble1 repmat(preamble2, 1, params.config_5g.numsym - 1)];
else
    preamble = [repmat(sts_t, 1, params.N_STS) lts_t((params.N_SC / 2 + 1):params.N_SC) lts_t lts_t];
end
params.preamble = preamble;

params.tx_syms_mat = data_symbols;
params.pilots_mat = pilot_symbols;

ifft_in_mat = zeros(params.N_SC, params.N_OFDM_SYMS);
ifft_in_mat(params.SC_IND_DATA, :) = data_symbols;
ifft_in_mat(params.SC_IND_PILOTS, :) = pilot_symbols;

tx_payload_mat = ifft(ifft_in_mat, params.N_SC, 1);

if params.CP_LEN > 0
    tx_cp = tx_payload_mat((end - params.CP_LEN + 1:end), :);
    tx_payload_mat = [tx_cp; tx_payload_mat];
end

tx_payload_vec = reshape(tx_payload_mat, 1, numel(tx_payload_mat));
params.tx_payload_vec = tx_payload_vec;

tx_vec = [preamble tx_payload_vec];
tx_vec_padded = [tx_vec zeros(1, params.N_ZERO_PAD)];
tx_vec_air = tx_vec_padded;
tx_vec_air = params.TX_SCALE .* tx_vec_air ./ max(abs(tx_vec_air));
params.TX_NUM_SAMPS = length(tx_vec_air);
tx_vec_air = tx_vec_air.';
