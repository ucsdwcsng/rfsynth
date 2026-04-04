function [tx_vec_air, params] = ofdm_tx(params)
params.N_DATA_SYMS = params.N_OFDM_SYMS * length(params.SC_IND_DATA);

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

inSig = randi([0 params.MOD_ORDER - 1], params.N_DATA_IND, params.N_OFDM_SYMS);
params.tx_data = inSig(:);
tx_syms_mat = qammod(inSig, params.MOD_ORDER, 'UnitAveragePower', true);
params.tx_syms_mat = tx_syms_mat;

pilots = params.pilots;
pilots_mat = repmat(pilots, 1, params.N_OFDM_SYMS);
params.pilots_mat = pilots_mat;

ifft_in_mat = zeros(params.N_SC, params.N_OFDM_SYMS);
ifft_in_mat(params.SC_IND_DATA, :) = tx_syms_mat;
ifft_in_mat(params.SC_IND_PILOTS, :) = pilots_mat;

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
end
