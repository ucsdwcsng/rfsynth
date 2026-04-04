function summary = run_synthetic_json(configPath)
%RUN_SYNTHETIC_JSON Headless synthetic-only runner for JSON configs.

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
    cfg = normalizeConfig(cfg, configPath);

    rx = atomic.Rx( ...
        asText(cfg.rxConfig.name), ...
        cfg.rxConfig.rxSampleRate_Hz, ...
        cfg.rxConfig.centerFreq_Hz, ...
        rowVector3(cfg.rxConfig.location));

    sigGen = VirtualSignalEngine();
    sigGen.addRxObj(rx);

    if isfield(cfg, 'sources')
        sources = cfg.sources;
        for iSource = 1:numel(sources)
            sigGen.addSource(buildSource(sources(iSource), cfg.rxConfig.rxSampleRate_Hz, iSource));
        end
    elseif isfield(cfg, 'signals')
        signals = cfg.signals;
        for iSignal = 1:numel(signals)
            defaultSource = struct( ...
                'name', "Source" + string(iSignal), ...
                'origin', "synthetic_json", ...
                'location', [0, 0, 0], ...
                'channelModel', "IDENTITY", ...
                'freqOffset_Hz', 0, ...
                'iqImbalance', [0, 0], ...
                'dcOffset', [0, 0], ...
                'signals', signals(iSignal));
            sigGen.addSource(buildSource(defaultSource, cfg.rxConfig.rxSampleRate_Hz, iSignal));
        end
    else
        error('run_synthetic_json:InvalidConfig', 'Config must define either sources or signals.');
    end

    flagOutputIqSamples = getFieldOr(cfg.generationParameters, 'flagOutputIqSamples', true);
    totalTime = cfg.generationParameters.tot_time;
    outputFolder = getFieldOr(cfg.generationParameters, 'outputFolder', '/tmp');
    outputBase = getFieldOr(cfg.generationParameters, 'outputBase', erase(string(getFilenameBase(configPath)), ".json"));

    samplesIQ = sigGen.generateSamples(0, totalTime, flagOutputIqSamples);
    metadataStr = sigGen.getMetadataJson();
    VirtualSignalEngine.writeDataFiles(samplesIQ, metadataStr, outputFolder, outputBase);

    metadataStruct = jsondecode(metadataStr);
    summary = struct( ...
        'configPath', string(configPath), ...
        'outputFolder', string(outputFolder), ...
        'outputBase', string(outputBase), ...
        'iqPath', fullfile(outputFolder, string(outputBase) + ".32cf"), ...
        'metadataPath', fullfile(outputFolder, string(outputBase) + ".json"), ...
        'scoringPath', fullfile(outputFolder, string(outputBase) + "_scoring.json"), ...
        'sampleCount', numel(samplesIQ), ...
        'sourceCount', numel(metadataStruct.sourceArray));

    fprintf('%s\n', jsonencode(summary, 'PrettyPrint', true));
end

function sourceObj = buildSource(sourceCfg, sampleRateHz, sourceIndex)
    sourceName = getFieldOr(sourceCfg, 'name', sprintf('Source%d', sourceIndex));
    sourceOrigin = getFieldOr(sourceCfg, 'origin', 'synthetic_json');
    sourceLocation = rowVector3(getFieldOr(sourceCfg, 'location', [0, 0, 0]));
    channelModel = getFieldOr(sourceCfg, 'channelModel', 'IDENTITY');
    freqOffsetHz = getFieldOr(sourceCfg, 'freqOffset_Hz', 0);
    iqImbalance = colVector2(getFieldOr(sourceCfg, 'iqImbalance', [0, 0]));
    dcOffset = colVector2(getFieldOr(sourceCfg, 'dcOffset', [0, 0]));

    imperfectionCfg = atomic.RFImperfections(freqOffsetHz, iqImbalance, dcOffset);
    sourceObj = atomic.Source( ...
        asText(sourceName), ...
        asText(sourceOrigin), ...
        sampleRateHz, ...
        sourceLocation, ...
        asText(channelModel), ...
        imperfectionCfg);

    signals = sourceCfg.signals;
    for iSignal = 1:numel(signals)
        signalCfg = signals(iSignal);
        signalArgs = structToVarargin(signalCfg.args);
        signalObj = feval(char("atomic." + string(signalCfg.type)), signalArgs{:});
        sourceObj.addSignal(signalObj);
    end
end

function cfg = normalizeConfig(cfg, configPath)
    cfg.generationParameters = normalizeGenerationParameters(cfg, configPath);
    cfg.rxConfig = normalizeRxConfig(cfg);

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

function generationParameters = normalizeGenerationParameters(cfg, configPath)
    generationParameters = getFieldOr(cfg, 'generationParameters', struct());
    outputCfg = getFieldOr(cfg, 'output', struct());

    generationParameters.flagOutputIqSamples = getFieldOr( ...
        generationParameters, 'flagOutputIqSamples', ...
        getFieldOr(outputCfg, 'flagOutputIqSamples', true));
    generationParameters.tot_time = getFieldOr( ...
        generationParameters, 'tot_time', ...
        getFieldOr(outputCfg, 'tot_time', 0.02));
    generationParameters.outputFolder = getFieldOr( ...
        generationParameters, 'outputFolder', ...
        getFieldOr(outputCfg, 'outputFolder', '/tmp'));
    generationParameters.outputBase = getFieldOr( ...
        generationParameters, 'outputBase', ...
        getFieldOr(outputCfg, 'outputBase', erase(string(getFilenameBase(configPath)), ".json")));
end

function rxConfig = normalizeRxConfig(cfg)
    if isfield(cfg, 'rxConfig')
        rxConfig = cfg.rxConfig;
    else
        rxCfg = getFieldOr(cfg, 'rx', struct());
        rxConfig = struct( ...
            'name', getFieldOr(rxCfg, 'name', "rx1"), ...
            'rxSampleRate_Hz', getFieldOr(rxCfg, 'rxSampleRate_Hz', getFieldOr(rxCfg, 'sampleRate_Hz', nan)), ...
            'centerFreq_Hz', getFieldOr(rxCfg, 'centerFreq_Hz', nan), ...
            'location', getFieldOr(rxCfg, 'location', [0, 0, 0]));
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
        if ~isfield(signalArgs, 'trafficType')
            signalArgs.trafficType = struct('type', "periodic", 'transmissionPerSec', 100);
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
    if isempty(s)
        out = {};
        return
    end

    fields = fieldnames(s);
    values = struct2cell(s);
    out = cell(1, 2 * numel(fields));
    out(1:2:end) = fields;
    out(2:2:end) = values;
end

function out = rowVector3(v)
    out = reshape(double(v), 1, []);
    assert(numel(out) == 3, 'Expected a 3-element row vector.');
end

function out = colVector2(v)
    out = reshape(double(v), [], 1);
    assert(numel(out) == 2, 'Expected a 2-element column vector.');
end

function out = asText(v)
    if isstring(v)
        out = char(v);
    elseif ischar(v)
        out = v;
    else
        out = char(string(v));
    end
end

function name = getFilenameBase(pathIn)
    [~, name, ext] = fileparts(pathIn);
    name = [name, ext];
end
