function summary = export_lte_channel_indices(configPath, outputFolder)
%EXPORT_LTE_CHANNEL_INDICES Export LTE channel/index masks for parity debugging.

    arguments
        configPath (1,:) char
        outputFolder (1,:) char = ''
    end

    thisFile = mfilename('fullpath');
    examplesDir = fileparts(thisFile);
    matlabRoot = fileparts(examplesDir);

    restoredefaultpath;
    addpath(genpath(fullfile(matlabRoot, 'lib')));
    addpath(examplesDir);

    cfg = jsondecode(fileread(configPath));
    cfg = normalizeAtomicConfigLocal(cfg, configPath);
    signalCfg = extractSingleSignalLocal(cfg);
    assert(string(signalCfg.type) == "LTE_DL_FDD", ...
        'export_lte_channel_indices:InvalidSignal', ...
        'Config must contain exactly one LTE_DL_FDD signal.');

    if isempty(outputFolder)
        outputFolder = char(cfg.generationParameters.outputFolder);
    end
    if ~exist(outputFolder, 'dir')
        mkdir(outputFolder);
    end

    signalArgv = structToVararginLocal(signalCfg.args);
    [~, info] = lteDlFddWaveform(signalArgv{:});
    enb = info.cfgLTE;
    if ~isfield(enb, 'NSubframe')
        enb.NSubframe = 0;
    end
    gridSize = [12 * enb.NDLRB, 14 * enb.TotSubframes];

    masks = struct();
    masks.crs = false(gridSize);
    masks.pcfich = false(gridSize);
    masks.phich = false(gridSize);
    masks.pdcch = false(gridSize);
    masks.pss = false(gridSize);
    masks.sss = false(gridSize);
    masks.pbch = false(gridSize);

    masks.crs(lteCellRSIndices(enb, 0, {'1based'})) = true;
    masks.pcfich(ltePCFICHIndices(enb, {'1based'})) = true;
    masks.phich(ltePHICHIndices(enb, {'1based'})) = true;
    masks.pdcch(ltePDCCHIndices(enb, {'1based'})) = true;
    if mod(enb.NSubframe, 10) == 0 || mod(enb.NSubframe, 10) == 5
        masks.pss(ltePSSIndices(enb, 0, {'1based'})) = true;
        masks.sss(lteSSSIndices(enb, 0, {'1based'})) = true;
    end
    if mod(enb.NSubframe, 10) == 0
        pbchIdx = ltePBCHIndices(enb, {'1based'});
        masks.pbch(pbchIdx) = true;
    end

    payload = struct();
    fields = fieldnames(masks);
    for iField = 1:numel(fields)
        payload.(fields{iField}) = masks.(fields{iField});
    end
    payload.gridSize = gridSize;
    payload.NDLRB = enb.NDLRB;
    payload.CyclicPrefix = string(enb.CyclicPrefix);
    payload.CFI = enb.CFI;
    payload.NCellID = enb.NCellID;

    outPath = fullfile(outputFolder, 'lte_channel_indices.json');
    fid = fopen(outPath, 'w');
    cleanup = onCleanup(@() fclose(fid));
    fwrite(fid, jsonencode(payload, 'PrettyPrint', true), 'char');

    summary = struct( ...
        'configPath', string(configPath), ...
        'outputFolder', string(outputFolder), ...
        'indicesPath', string(outPath));
    fprintf('%s\n', jsonencode(summary, 'PrettyPrint', true));
end

function cfg = normalizeAtomicConfigLocal(cfg, configPath)
    generation = getFieldOrLocal(cfg, 'generationParameters', struct());
    output = getFieldOrLocal(cfg, 'output', struct());
    cfg.generationParameters = struct( ...
        'outputFolder', getFieldOrLocal(generation, 'outputFolder', getFieldOrLocal(output, 'outputFolder', '/tmp')), ...
        'outputBase', getFieldOrLocal(generation, 'outputBase', getFieldOrLocal(output, 'outputBase', erase(string(getFilenameBaseLocal(configPath)), ".json"))), ...
        'seed', getFieldOrLocal(generation, 'seed', getFieldOrLocal(output, 'seed', [])));

    if isfield(cfg, 'signals')
        cfg.signals = normalizeSignalsLocal(cfg.signals);
    end
    if isfield(cfg, 'sources')
        sources = cfg.sources;
        for iSource = 1:numel(sources)
            if isfield(sources(iSource), 'signals')
                sources(iSource).signals = normalizeSignalsLocal(sources(iSource).signals);
            end
        end
        cfg.sources = sources;
    end
end

function signalCfg = extractSingleSignalLocal(cfg)
    if isfield(cfg, 'sources')
        assert(numel(cfg.sources) == 1, 'Expected exactly one source.');
        signals = cfg.sources(1).signals;
    elseif isfield(cfg, 'signals')
        signals = cfg.signals;
    else
        error('export_lte_channel_indices:InvalidConfig', 'Config must define sources or signals.');
    end

    if iscell(signals)
        assert(numel(signals) == 1, 'Expected exactly one signal.');
        signalCfg = signals{1};
    else
        assert(numel(signals) == 1, 'Expected exactly one signal.');
        signalCfg = signals(1);
    end
end

function signalsOut = normalizeSignalsLocal(signalsIn)
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

function out = getFieldOrLocal(s, fieldName, defaultValue)
    if isfield(s, fieldName)
        out = s.(fieldName);
    else
        out = defaultValue;
    end
end

function out = structToVararginLocal(s)
    fields = fieldnames(s);
    values = struct2cell(s);
    out = cell(1, 2 * numel(fields));
    out(1:2:end) = fields;
    out(2:2:end) = values;
end

function name = getFilenameBaseLocal(pathIn)
    [~, name, ext] = fileparts(pathIn);
    name = [name, ext];
end
