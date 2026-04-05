function summary = run_atomic_test_vector(configPath)
%RUN_ATOMIC_TEST_VECTOR Generate one raw atomic burst from JSON for sample-level comparison.

    arguments
        configPath (1,:) char
    end

    thisFile = mfilename('fullpath');
    examplesDir = fileparts(thisFile);
    matlabRoot = fileparts(examplesDir);

    restoredefaultpath;
    addpath(genpath(fullfile(matlabRoot, 'lib')));
    addpath(examplesDir);

    cfg = jsondecode(fileread(configPath));
    cfg = normalizeAtomicConfig(cfg, configPath);

    if isfield(cfg.generationParameters, 'seed') && ~isempty(cfg.generationParameters.seed)
        rng(double(cfg.generationParameters.seed), 'twister');
    end

    signalCfg = extractSingleSignal(cfg);
    samplesIQ = generateAtomicTransmission(signalCfg, cfg);

    outputFolder = char(cfg.generationParameters.outputFolder);
    outputBase = char(cfg.generationParameters.outputBase);
    if ~exist(outputFolder, 'dir')
        mkdir(outputFolder);
    end

    iqPath = fullfile(outputFolder, char(string(outputBase) + ".32cf"));
    write_cf32_file(iqPath, samplesIQ);

    summary = struct( ...
        'configPath', string(configPath), ...
        'outputFolder', string(outputFolder), ...
        'outputBase', string(outputBase), ...
        'iqPath', string(iqPath), ...
        'sampleCount', numel(samplesIQ), ...
        'signalType', string(signalCfg.type));

    fprintf('%s\n', jsonencode(summary, 'PrettyPrint', true));
end

function samplesIQ = generateAtomicTransmission(signalCfg, cfg)
    signalArgs = signalCfg.args;
    signalType = string(signalCfg.type);
    manualTypes = ["Pam", "Psk", "Fsk", "Cpfsk", "Gfsk", "Gmsk", "Msk", "RandomSymbol", "Ds3", "FreqHopping", "WidebandThermalWgn"];
    if any(signalType == manualTypes)
        samplesIQ = generateManualTransmission(signalType, signalArgs, cfg);
        return
    end

    varargin = structToVarargin(signalArgs);
    signalObj = feval(char("atomic." + signalType), varargin{:});
    samplesIQ = signalObj.generateTransmission();
    if ~strcmp(signalType, "WidebandThermalWgn")
        samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(signalArgs, 'txPower_db', 0));
    end
end

function samplesIQ = generateManualTransmission(signalType, args, cfg)
    vec = [];
    if isfield(args, 'testVectorPath') && strlength(string(args.testVectorPath)) > 0
        vec = load_atomic_test_vector(args.testVectorPath);
    end

    switch signalType
        case "Pam"
            modOrder = double(getFieldOr(args, 'modOrder', 4));
            sps = double(getFieldOr(args, 'samplesPerSymbol', 8));
            beta = double(getFieldOr(args, 'beta', 0.35));
            span = double(getFieldOr(args, 'span', 10));
            if ~isempty(vec) && isfield(vec.payload, 'symbols')
                y = vec.payload.symbols(:);
            elseif ~isempty(vec) && isfield(vec.payload, 'symbol_indices')
                x = double(vec.payload.symbol_indices(:));
                y = pammod(x, modOrder, 0, 'gray');
            else
                nSym = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * double(getFieldOr(args, 'transmissionRate_Hz', 1e6))));
                x = randi([0 modOrder - 1], nSym, 1);
                y = pammod(x, modOrder, 0, 'gray');
            end
            y = upsample(y, sps);
            rrc = rcosdesign(beta, span, sps);
            rrc = rrc.' / rms(rrc);
            samplesIQ = complex(conv(y, rrc, 'same'), 0);
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "Psk"
            modOrder = double(getFieldOr(args, 'modOrder', 4));
            sps = double(getFieldOr(args, 'samplesPerSymbol', 8));
            beta = double(getFieldOr(args, 'beta', 0.35));
            span = double(getFieldOr(args, 'span', 10));
            if ~isempty(vec) && isfield(vec.payload, 'symbols')
                y1 = vec.payload.symbols(:);
            elseif ~isempty(vec) && isfield(vec.payload, 'symbol_indices')
                x = double(vec.payload.symbol_indices(:));
                y1 = pskmod(x, modOrder, pi / modOrder, 'gray');
            else
                nSym = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * double(getFieldOr(args, 'transmissionRate_Hz', 1e6))));
                x = randi([0 modOrder - 1], nSym, 1);
                y1 = pskmod(x, modOrder, pi / modOrder, 'gray');
            end
            y2 = upsample(y1, sps);
            rrc = rcosdesign(beta, span, sps);
            rrc = rrc.' / rms(rrc);
            samplesIQ = conv(y2, rrc, 'same');
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "Fsk"
            modOrder = double(getFieldOr(args, 'modOrder', 2));
            sps = double(getFieldOr(args, 'samplesPerSymbol', 8));
            symbolRate = double(getFieldOr(args, 'transmissionRate_Hz', 250e3));
            sampleFreq = symbolRate * sps;
            freqDev = double(getFieldOr(args, 'freqDev', 0.25));
            if ~isempty(vec) && isfield(vec.payload, 'symbol_indices')
                x = double(vec.payload.symbol_indices(:));
            else
                nSym = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * symbolRate));
                x = randi([0 modOrder - 1], nSym, 1);
            end
            freqSep = freqDev * sampleFreq / max(modOrder - 1, 1);
            samplesIQ = fskmod(x, modOrder, freqSep, sps, sampleFreq, 'discont');
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "Cpfsk"
            modOrder = double(getFieldOr(args, 'modOrder', 2));
            sps = double(getFieldOr(args, 'samplesPerSymbol', 8));
            modulationIndex = double(getFieldOr(args, 'modulationIndex', 0.5));
            if ~isempty(vec) && isfield(vec.payload, 'symbol_indices')
                x = double(vec.payload.symbol_indices(:));
            else
                nSym = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * double(getFieldOr(args, 'transmissionRate_Hz', 250e3))));
                x = randi([0 modOrder - 1], nSym, 1);
            end
            modObj = comm.CPFSKModulator('ModulationOrder', modOrder, 'ModulationIndex', modulationIndex, 'SamplesPerSymbol', sps);
            meanOffset = mean(0:modOrder - 1);
            samplesIQ = modObj(2 * (x - meanOffset));
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "Gfsk"
            modOrder = double(getFieldOr(args, 'modOrder', 2));
            sps = double(getFieldOr(args, 'samplesPerSymbol', 8));
            bt = double(getFieldOr(args, 'bandwidthTimeProduct', 0.35));
            modulationIndex = double(getFieldOr(args, 'modulationIndex', 0.5));
            if ~isempty(vec) && isfield(vec.payload, 'symbol_indices')
                x = double(vec.payload.symbol_indices(:));
            else
                nSym = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * double(getFieldOr(args, 'transmissionRate_Hz', 250e3))));
                x = randi([0 modOrder - 1], nSym, 1);
            end
            modObj = comm.CPMModulator('ModulationOrder', modOrder, 'FrequencyPulse', 'Gaussian', 'BandwidthTimeProduct', bt, 'ModulationIndex', modulationIndex, 'SamplesPerSymbol', sps);
            meanOffset = mean(0:modOrder - 1);
            samplesIQ = modObj(2 * (x - meanOffset));
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "Gmsk"
            sps = double(getFieldOr(args, 'samplesPerSymbol', 8));
            bt = double(getFieldOr(args, 'bandwidthTimeProduct', 0.35));
            pulseLength = double(getFieldOr(args, 'pulseLength', 4));
            if ~isempty(vec) && isfield(vec.payload, 'bits')
                bits = logical(vec.payload.bits(:));
            else
                nBits = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * double(getFieldOr(args, 'transmissionRate_Hz', 250e3))));
                bits = logical(randi([0 1], nBits, 1));
            end
            modObj = comm.GMSKModulator('BitInput', true, 'BandwidthTimeProduct', bt, 'PulseLength', pulseLength, 'SamplesPerSymbol', sps);
            samplesIQ = modObj(bits);
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "Msk"
            sps = double(getFieldOr(args, 'samplesPerSymbol', 8));
            modOrder = double(getFieldOr(args, 'modOrder', 2));
            if ~isempty(vec) && isfield(vec.payload, 'symbol_indices')
                x = double(vec.payload.symbol_indices(:));
            else
                nSym = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * double(getFieldOr(args, 'transmissionRate_Hz', 250e3))));
                x = randi([0 modOrder - 1], nSym, 1);
            end
            samplesIQ = mskmod(x, sps);
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "RandomSymbol"
            modOrder = double(getFieldOr(args, 'modOrder', 4));
            sps = double(getFieldOr(args, 'samplesPerSymbol', 4));
            if ~isempty(vec) && isfield(vec.payload, 'symbols')
                symbols = vec.payload.symbols(:);
            elseif ~isempty(vec) && isfield(vec.payload, 'symbol_indices')
                phases = double(vec.payload.symbol_indices(:));
                symbols = exp(2j * pi * phases / modOrder);
            else
                nSym = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * double(getFieldOr(args, 'transmissionRate_Hz', 1e6))));
                phases = randi([0 modOrder - 1], nSym, 1);
                symbols = exp(2j * pi * phases / modOrder);
            end
            samplesIQ = repelem(symbols, sps);
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "Ds3"
            chipsPerSymbol = double(getFieldOr(args, 'chipsPerSymbol', 1024));
            modOrder = double(getFieldOr(args, 'modOrder', 2));
            spreadType = double(getFieldOr(args, 'spreadType', 1));
            samplesPerChip = double(getFieldOr(args, 'samplesPerChip', 2));
            if ~isempty(vec) && isfield(vec.payload, 'symbol_indices')
                x = double(vec.payload.symbol_indices(:));
            else
                symbolRate = double(getFieldOr(args, 'bandwidth_Hz', 20e6)) / (2 * chipsPerSymbol);
                nSym = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.001)) * symbolRate));
                x = randi([0 modOrder - 1], nSym, 1);
            end
            y = pskmod(x, modOrder, pi / modOrder, 'gray');
            if ~isempty(vec) && isfield(vec.payload, 'spread_code')
                spreadCode = double(vec.payload.spread_code);
            else
                spreadCode = 2 * randi([0 1], chipsPerSymbol, 1) - 1;
            end
            if spreadType == 1 || isvector(spreadCode)
                samplesIQ = kron(y, spreadCode(:));
            else
                spreadCode = double(spreadCode);
                samplesIQ = y.' .* spreadCode(:, 1:numel(y));
                samplesIQ = samplesIQ(:);
            end
            samplesIQ = repmat(samplesIQ, 1, samplesPerChip)';
            samplesIQ = samplesIQ(:);
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "FreqHopping"
            totalSamples = max(1, round(double(getFieldOr(args, 'transmissionTotTime', 0.004)) * double(getFieldOr(args, 'transmissionRate_Hz', 10e6))));
            guardSamples = round(double(getFieldOr(args, 'guardTime_s', 50e-6)) * double(getFieldOr(args, 'transmissionRate_Hz', 10e6)));
            nHops = double(getFieldOr(args, 'nHops', 5));
            hopSamples = max(1, floor(max(1, totalSamples - guardSamples * max(nHops - 1, 0)) / nHops));
            if ~isempty(vec) && isfield(vec.payload, 'hop_centers_hz')
                hopCenters = double(vec.payload.hop_centers_hz(:));
            else
                hopCenters = linspace( ...
                    -double(getFieldOr(args, 'bandwidth_Hz', 10e6)) / 2 + double(getFieldOr(args, 'bandwidthPerHop_Hz', 500e3)) / 2, ...
                    double(getFieldOr(args, 'bandwidth_Hz', 10e6)) / 2 - double(getFieldOr(args, 'bandwidthPerHop_Hz', 500e3)) / 2, ...
                    nHops);
                hopCenters = hopCenters(randperm(numel(hopCenters)));
            end
            segments = cell(numel(hopCenters), 1);
            for hopIdx = 1:numel(hopCenters)
                n = (0:hopSamples - 1).';
                segments{hopIdx} = exp(2j * pi * hopCenters(hopIdx) / double(getFieldOr(args, 'transmissionRate_Hz', 10e6)) .* n);
            end
            samplesIQ = segments{1};
            for hopIdx = 2:numel(hopCenters)
                samplesIQ = [samplesIQ; zeros(guardSamples, 1); segments{hopIdx}]; %#ok<AGROW>
            end
            if numel(samplesIQ) < totalSamples
                samplesIQ = [samplesIQ; zeros(totalSamples - numel(samplesIQ), 1)];
            else
                samplesIQ = samplesIQ(1:totalSamples);
            end
            samplesIQ = scaleTxPowerLocal(samplesIQ, getFieldOr(args, 'txPower_db', 0));

        case "WidebandThermalWgn"
            if ~isempty(vec) && isfield(vec.payload, 'samples')
                samplesIQ = 0.02 * vec.payload.samples(:);
            else
                nSamples = max(1, round(double(getFieldOr(cfg.generationParameters, 'tot_time', 0.02)) * double(getFieldOr(args, 'bandwidth_Hz', 20e6))));
                samplesIQ = 0.02 * complex(randn(nSamples, 1), randn(nSamples, 1)) / sqrt(2);
            end

        otherwise
            error('run_atomic_test_vector:UnsupportedSignal', 'Unsupported manual signal type %s', signalType);
    end
end

function out = scaleTxPowerLocal(in, txPowerDb)
    if isnan(txPowerDb)
        out = in;
        return
    end
    sigPow = rms(in);
    if sigPow == 0
        out = in;
        return
    end
    out = (db2mag(txPowerDb) / sigPow) .* in;
end

function cfg = normalizeAtomicConfig(cfg, configPath)
    generation = getFieldOr(cfg, 'generationParameters', struct());
    output = getFieldOr(cfg, 'output', struct());
    cfg.generationParameters = struct( ...
        'outputFolder', getFieldOr(generation, 'outputFolder', getFieldOr(output, 'outputFolder', '/tmp')), ...
        'outputBase', getFieldOr(generation, 'outputBase', getFieldOr(output, 'outputBase', erase(string(getFilenameBase(configPath)), ".json"))), ...
        'seed', getFieldOr(generation, 'seed', getFieldOr(output, 'seed', [])));

    if isfield(cfg, 'signals')
        cfg.signals = normalizeSignals(cfg.signals);
    end
    if isfield(cfg, 'sources')
        sources = cfg.sources;
        for iSource = 1:numel(sources)
            if isfield(sources(iSource), 'signals')
                sources(iSource).signals = normalizeSignals(sources(iSource).signals);
            end
        end
        cfg.sources = sources;
    end
end

function signalCfg = extractSingleSignal(cfg)
    if isfield(cfg, 'sources')
        assert(numel(cfg.sources) == 1, 'Atomic compare expects exactly one source.');
        signals = cfg.sources(1).signals;
    elseif isfield(cfg, 'signals')
        signals = cfg.signals;
    else
        error('run_atomic_test_vector:InvalidConfig', 'Config must define sources or signals.');
    end

    if iscell(signals)
        assert(numel(signals) == 1, 'Atomic compare expects exactly one signal.');
        signalCfg = signals{1};
    else
        assert(numel(signals) == 1, 'Atomic compare expects exactly one signal.');
        signalCfg = signals(1);
    end
end

function signalsOut = normalizeSignals(signalsIn)
    signalTemplate = struct('type', "", 'args', struct());
    if isempty(signalsIn)
        signalsOut = repmat(signalTemplate, size(signalsIn));
        return
    end

    if iscell(signalsIn)
        signalItems = signalsIn;
    else
        signalItems = num2cell(signalsIn);
    end

    signalsOut = repmat(signalTemplate, 1, numel(signalItems));
    for iSignal = 1:numel(signalItems)
        signalCfg = signalItems{iSignal};
        assert(isfield(signalCfg, 'type'), 'Every signal entry must define a type field.');
        signalType = signalCfg.type;
        if isfield(signalCfg, 'args')
            signalArgs = signalCfg.args;
        else
            signalArgs = rmfield(signalCfg, 'type');
        end
        signalsOut(iSignal) = struct('type', signalType, 'args', signalArgs);
    end
end

function out = getFieldOr(s, fieldName, defaultValue)
    if isfield(s, fieldName)
        out = s.(fieldName);
    else
        out = defaultValue;
    end
end

function out = structToVarargin(s)
    fields = fieldnames(s);
    values = struct2cell(s);
    out = cell(1, 2 * numel(fields));
    out(1:2:end) = fields;
    out(2:2:end) = values;
end

function name = getFilenameBase(pathIn)
    [~, name, ext] = fileparts(pathIn);
    name = [name, ext];
end
