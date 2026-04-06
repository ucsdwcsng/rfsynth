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
                tb_size = lookupTransportBlockSizeLocal(opts, subframe_index);
                if ~isempty(tb_size)
                    msg_len = msg_len + tb_size;
                else
                    cfgLTE.NSubframe = mod(subframe_index, 10);
                    [~, pdschInfo] = ltePDSCHIndices(cfgLTE, pdsch, pdsch.PRBSet, {'1based'});
                    msg_len = msg_len + pdschInfo.G;
                end
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

function tbSize = lookupTransportBlockSizeLocal(opts, subframeIndex)
    tbSize = [];
    if opts.NDLRB == 6 && strcmpi(string(opts.CP), "Normal") && strcmpi(string(opts.modulation), "QPSK")
        schedule = [328, 712, 712, 712, 712, 600, 712, 712, 712, 712];
        tbSize = schedule(mod(subframeIndex, numel(schedule)) + 1);
        return
    end

    if ~strcmpi(string(opts.CP), "Normal")
        return
    end

    if strcmpi(string(opts.modulation), "QPSK")
        switch opts.NDLRB
            case 15
                tbSize = 1544;
            case 25
                tbSize = 3112;
            case 50
                tbSize = 6200;
            case 75
                tbSize = 9144;
            case 100
                tbSize = 14112;
        end
        return
    end

    if strcmpi(string(opts.modulation), "16QAM")
        switch opts.NDLRB
            case 6
                tbSize = 1032;
            case 15
                tbSize = 3880;
            case 25
                tbSize = 6456;
            case 50
                tbSize = 14112;
            case 75
                tbSize = 21384;
            case 100
                tbSize = 28336;
        end
    end
end
