function [dataIQ, info] = lteDlFddWaveform(varargin)
%LTEDLFDDWAVEFORM Create one narrow LTE DL FDD waveform for oracle-backed parity.

    defaults = struct( ...
        'centerFreq_Hz', 763e6, ...
        'nPacket', 1, ...
        'idleTime', 0, ...
        'TotSubframes', 1, ...
        'message', [], ...
        'messagePath', "", ...
        'NDLRB', 6, ...
        'CP', 'Normal', ...
        'modulation', 'QPSK');
    [opts, ~] = parseOptions(defaults, varargin{:});

    [bandwidth_Hz, transmissionRate_Hz] = lteDlFddPresetRates(opts.NDLRB); %#ok<ASGLU>

    cfgLTE = struct();
    cfgLTE.TotSubframes = opts.TotSubframes;
    cfgLTE.NDLRB = opts.NDLRB;
    cfgLTE.CyclicPrefix = opts.CP;
    cfgLTE.PHICHDuration = 'Normal';
    cfgLTE.DuplexMode = 'FDD';
    cfgLTE.CFI = 2;
    cfgLTE.Ng = 'Sixth';
    cfgLTE.CellRefP = 1;
    cfgLTE.NCellID = 10;

    pdsch = struct();
    pdsch.NLayers = 4;
    pdsch.TxScheme = 'Port0';
    pdsch.RNTI = 1;
    pdsch.RV = 0;
    pdsch.PRBSet = (0:cfgLTE.NDLRB-1).';
    pdsch.Modulation = opts.modulation;

    if isempty(opts.message)
        if strlength(string(opts.messagePath)) > 0
            payload = jsondecode(fileread(char(opts.messagePath)));
            if isfield(payload, 'message_bits')
                message = reshape(double(payload.message_bits), [], 1);
            elseif isfield(payload, 'payload') && isfield(payload.payload, 'message_bits')
                message = reshape(double(payload.payload.message_bits), [], 1);
            else
                message = reshape(double(payload), [], 1);
            end
        else
            msg_len = 0;
            for subframe_index = 0 : cfgLTE.TotSubframes - 1
                cfgLTE.NSubframe = mod(subframe_index, 10);
                [~, pdschInfo] = ltePDSCHIndices(cfgLTE, pdsch, pdsch.PRBSet, {'1based'});
                msg_len = msg_len + pdschInfo.G;
            end
            message = randi([0 1], msg_len, 1);
        end
    else
        msg_len = 0;
        message = opts.message(:);
    end

    cfgLTE.PDSCH = pdsch;
    dataIQ = lteRMCDLTool(cfgLTE, message);

    info = struct( ...
        'cfgLTE', cfgLTE, ...
        'message', message, ...
        'centerFreq_Hz', opts.centerFreq_Hz, ...
        'bandwidth_Hz', bandwidth_Hz, ...
        'transmissionRate_Hz', transmissionRate_Hz, ...
        'modulation', string(opts.modulation));
end
