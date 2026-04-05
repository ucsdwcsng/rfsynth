function summary = export_wlan_field_artifacts(configPath, outputFolder)
%EXPORT_WLAN_FIELD_ARTIFACTS Export MATLAB WLAN legacy fields for parity debugging.

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
    assert(string(signalCfg.type) == "WlanNonHT80211g", ...
        'export_wlan_field_artifacts:InvalidSignal', ...
        'Config must contain exactly one WlanNonHT80211g signal.');

    signalArgv = structToVararginLocal(signalCfg.args);
    signalObj = feval("atomic.WlanNonHT80211g", signalArgv{:});
    if isempty(outputFolder)
        outputFolder = char(cfg.generationParameters.outputFolder);
    end
    if ~exist(outputFolder, 'dir')
        mkdir(outputFolder);
    end

    lstf = wlanLSTF(signalObj.cfgNonHT, 'OversamplingFactor', 1);
    lltf = wlanLLTF(signalObj.cfgNonHT, 'OversamplingFactor', 1);
    lsig = wlanLSIG(signalObj.cfgNonHT, 'OversamplingFactor', 1);
    data = wlanNonHTData( ...
        double(signalObj.message(:)), ...
        signalObj.cfgNonHT, ...
        signalObj.scramblerInitialization, ...
        OversamplingFactor=1);

    write_cf32_file(fullfile(outputFolder, 'lstf.32cf'), lstf);
    write_cf32_file(fullfile(outputFolder, 'lltf.32cf'), lltf);
    write_cf32_file(fullfile(outputFolder, 'lsig.32cf'), lsig);
    write_cf32_file(fullfile(outputFolder, 'nonht_data.32cf'), data);

    info = struct( ...
        'message_bits', logical(signalObj.message(:)).', ...
        'scramblerInitialization', double(signalObj.scramblerInitialization), ...
        'psduLength_bytes', double(signalObj.cfgNonHT.PSDULength), ...
        'lstf_len', numel(lstf), ...
        'lltf_len', numel(lltf), ...
        'lsig_len', numel(lsig), ...
        'nonht_data_len', numel(data));
    infoPath = fullfile(outputFolder, 'wlan_fields_info.json');
    fid = fopen(infoPath, 'w');
    cleanup = onCleanup(@() fclose(fid));
    fwrite(fid, jsonencode(info, 'PrettyPrint', true), 'char');

    summary = struct( ...
        'configPath', string(configPath), ...
        'outputFolder', string(outputFolder), ...
        'lstfPath', string(fullfile(outputFolder, 'lstf.32cf')), ...
        'lltfPath', string(fullfile(outputFolder, 'lltf.32cf')), ...
        'lsigPath', string(fullfile(outputFolder, 'lsig.32cf')), ...
        'nonhtDataPath', string(fullfile(outputFolder, 'nonht_data.32cf')), ...
        'infoPath', string(infoPath));
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
        error('export_wlan_field_artifacts:InvalidConfig', 'Config must define sources or signals.');
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
