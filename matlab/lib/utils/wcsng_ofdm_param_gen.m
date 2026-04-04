function [params] = wcsng_ofdm_param_gen(varargin)
if nargin < 1
    N_SC = 64;
else
    N_SC = [];
end

default_ofdm_type = "WLAN";
default_N_SC = 64;

p = inputParser;
validScalarPosNum = @(x) isnumeric(x) && isscalar(x) && (x > 0);
addOptional(p, 'ofdm_type', default_ofdm_type, @isstring);
addOptional(p, 'N_SC', default_N_SC, validScalarPosNum);
parse(p, varargin{:});

if isempty(N_SC)
    N_SC = p.Results.N_SC;
end

switch p.Results.ofdm_type
    case "5GNR"
        params.config_5g.init_cp = 88;
        params.config_5g.numsym = 14;
    case "WLAN"
    otherwise
        error("Unknown OFDM Type");
end

params.WRITE_PNG_FILES = 0;
params.plot_flag = 0;
params.CHANNEL = 11;
params.calc_stats = 1;
params.cf = 201;
params.N_OFDM_SYMS = 50;
params.MOD_ORDER = 2;
params.TX_SCALE = 1.0;
params.N_ZERO_PAD = 0;

params = ofdm_param_gen_arb(N_SC, params);

params.FFT_OFFSET = 4;
params.LTS_CORR_THRESH = 0.8;
params.DO_APPLY_CFO_CORRECTION = 1;
params.DO_APPLY_PHASE_ERR_CORRECTION = 1;
params.DO_APPLY_SFO_CORRECTION = 1;
params.DO_DECODE = 1;
params.example_mode_string = 'sim';
params.channel_coding = .5;
params.trellis_end_length = 8;
params.mimo_tx = 2;
params.mimo_rx = 4;
params.num_strm = 1;
params.TX_SPATIAL_STREAM_SHIFT = 3;
params.num_strm_rx = 1;
params.num_packets = 1;
params.packet_step_size = 1;
end

function [params] = ofdm_param_gen_arb(N_SC, params)
params.N_SC = N_SC;
params.SAMP_FREQ = 20e6;
params.CP_LEN = round(16 / 20e6 * params.SAMP_FREQ);
params.N_STS = 10;

num_filled_sc = round(params.N_SC * 52 / 64);
num_filled_sc = num_filled_sc + mod(num_filled_sc, 2);

num_pilots_needed = round(num_filled_sc / 13);
num_pilots_needed = num_pilots_needed + mod(num_pilots_needed, 2);

FILLED_SC_IND = [2:1:(num_filled_sc / 2 + 1) (params.N_SC - num_filled_sc / 2 + 1):params.N_SC];
params.FILLED_SC_IND = FILLED_SC_IND;

left_cut = linspace(2, (num_filled_sc / 2 + 1), (num_pilots_needed / 2) + 1);
right_cut = linspace((params.N_SC - num_filled_sc / 2 + 1), params.N_SC, (num_pilots_needed / 2) + 1);
left_mean = round((left_cut(1:end-1) + left_cut(2:end)) / 2);
right_mean = round((right_cut(1:end-1) + right_cut(2:end)) / 2);

params.SC_IND_PILOTS = [left_mean right_mean];
pilot_screw = [1,1,1,1,-1,-1,-1,1,-1,-1,-1,-1,1,1,-1,1,-1,-1,1,1,-1,1,1,-1,1,1,1,1,1,1,-1,1,1,1,-1,1,1,-1,-1,1,1,1,-1,1,-1,-1,-1,1,-1,1,-1,-1,1,-1,-1,1,1,1,1,1,-1,-1,1,1,-1,-1,1,-1,1,-1,1,1,-1,-1,-1,1,1,-1,-1,-1,-1,1,-1,-1,1,-1,1,1,1,1,-1,1,-1,1,1,-1,-1,1,1,-1,1,-1,-1,1,1,-1,-1,-1,-1,-1,-1,-1];
pilot_screw_rep = repmat(pilot_screw, 1, ceil(num_pilots_needed / length(pilot_screw)));
params.pilots = pilot_screw_rep(1:num_pilots_needed).';
params.SC_IND_DATA = setxor(FILLED_SC_IND, params.SC_IND_PILOTS);
params.N_DATA_IND = length(params.SC_IND_DATA);

sts_f = zeros(1, 64);
sts_f(1:27) = [0 0 0 0 -1-1i 0 0 0 -1-1i 0 0 0 1+1i 0 0 0 1+1i 0 0 0 1+1i 0 0 0 1+1i 0 0];
sts_f(39:64) = [0 0 1+1i 0 0 0 -1-1i 0 0 0 1+1i 0 0 0 -1-1i 0 0 0 -1-1i 0 0 0 1+1i 0 0 0];
sts_t = ifft(sqrt(13 / 6) .* sts_f, 64);
sts_t = sts_t(1:16);
params.sts_t = sts_t;

gold_order = log2(params.N_SC);
switch params.N_SC
    case 64
        lts_f = [0 1 -1 -1 1 1 -1 1 -1 1 -1 -1 -1 -1 -1 1 1 -1 -1 1 -1 1 -1 1 1 1 1 0 0 0 0 0 0 0 0 0 0 0 1 1 -1 -1 1 1 -1 1 -1 1 1 1 1 1 1 -1 -1 1 1 -1 1 -1 1 1 1 1];
        params.pilots = [1 1 -1 1].';
        params.SC_IND_PILOTS = [8 22 44 58];
        params.SC_IND_DATA = setxor(FILLED_SC_IND, params.SC_IND_PILOTS);
    case 128
        pol1 = [7 3 0];
        pol2 = [7 3 2 1 0];
    case 256
        lts_256 = [-1,-1,-1,1,-1,-1,-1,-1,-1,1,1,-1,1,-1,1,-1,-1,1,-1,-1,-1,1,-1,-1,-1,-1,1,-1,1,-1,-1,1,1,1,-1,1,-1,1,1,1,1,1,1,-1,-1,-1,1,1,-1,-1,-1,-1,1,-1,1,1,1,1,-1,-1,-1,-1,-1,1,-1,-1,-1,1,1,-1,-1,1,-1,1,-1,1,1,1,1,-1,1,-1,-1,-1,1,-1,1,-1,1,-1,1,-1,-1,1,1,-1,1,-1,1,-1,1,-1,1,1,-1,1,1,-1,-1,-1,-1,1,-1,1,-1,1,-1,-1,1,-1,-1,-1,1,-1,-1,1,-1,1,1,-1,-1,1,1,1,-1,-1,1,-1,1,-1,1,1,-1,1,1,-1,1,-1,-1,1,1,1,-1,1,-1,1,1,-1,-1,-1,-1,-1,1,1,1,1,1,-1,1,-1,-1,-1,-1,-1,-1,-1,-1,1,-1,-1,1,-1,-1,-1,1,1,-1,1,-1,1,-1,-1,-1,1,-1,-1,-1,1,1,-1,-1,1,1,-1,1,-1,1,-1,-1,-1,-1,1,-1,-1,-1,-1,1,1,1,1,1,-1,1,-1,-1,-1,1,1,1,1,-1,1,-1,-1,-1,1,1,1,1,1,-1,-1,-1,-1,1,1,1,-1,-1,-1,1,-1,1,1,-1,1];
        lts_f = zeros(1, params.N_SC);
        lts_f(FILLED_SC_IND) = lts_256(1:num_filled_sc);
    case 512
        pol1 = [9 4 0];
        pol2 = [9 6 4 3 0];
    case 1024
        pol1 = [10 3 0];
        pol2 = [10 8 3 2 0];
    case 2048
        pol1 = [11 2 0];
        pol2 = [11 8 5 2 0];
    otherwise
        error('Cannot generate PN sequence for given N_SC');
end

if gold_order ~= 6 && gold_order ~= 8
    init_cond1 = zeros(1, gold_order);
    init_cond2 = zeros(1, gold_order);
    init_cond1(end) = 1;
    init_cond2(end) = 1;
    goldseq = comm.GoldSequence( ...
        'FirstPolynomial', pol1, ...
        'SecondPolynomial', pol2, ...
        'FirstInitialConditions', init_cond1, ...
        'SecondInitialConditions', init_cond2, ...
        'Index', 4, ...
        'SamplesPerFrame', num_filled_sc);
    gold_pn_seq = goldseq();
    gold_pn_seq = 2 * gold_pn_seq - 1;
    lts_f = zeros(1, params.N_SC);
    lts_f(FILLED_SC_IND) = gold_pn_seq;
end

lts_t = ifft(lts_f, params.N_SC);
params.lts_f = lts_f;
params.lts_t = lts_t;
end
