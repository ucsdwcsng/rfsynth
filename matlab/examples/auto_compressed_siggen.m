function auto_compressed_siggen(filename)
    % Read YAML file
    config = yaml.loadFile(filename,"ConvertToArray", true);

    % Generation parameters
    flagOutputIqSamples = config.generationParameters.flagOutputIqSamples;
    tot_time = config.generationParameters.tot_time;
    outputFolder = config.generationParameters.outputFolder;
    filePrefix = config.generationParameters.filePrefix;

    % Rx configuration
    rx = atomic.Rx(config.rxConfig.name, config.rxConfig.rxSampleRate_Hz, config.rxConfig.centerFreq_Hz, config.rxConfig.location);

    % Instantiate compressed engine
    compGen = CompressedEngine();
    compGen.addRxObj(rx);

    % Tx configuration and add Tx objects to the engine
    for i = 1:length(config.txConfig)
        txConf = config.txConfig(i);
        tx = atomic.Tx(txConf.sampleRate_Hz,0, txConf.location, txConf.centerFreqRange_Hz);
        compGen.addTxObj(tx);
    end

    % Loop through signals and add them to the engine
    signals = config.signals;
    for i = 1:length(signals)
        signal = signals(i);
        signalArgs = namedargs2cell(signal.args);
        signalObj = feval("atomic."+signal.type, signalArgs{:});

        % Add signal to the CompressedEngine
        compGen.addSignal(signalObj);
    end

    % Map signals to Tx and Source
    compGen.mapSignalsToTxandSource();

    % Generate samples
    [samplesIQ, samplesPerChunk] = compGen.generateSamplesCompressed(0, tot_time, flagOutputIqSamples);
    metadataStr = compGen.getMetadataJson();

    % Save engine outputs
    txSigMap = compGen.getSignalTxMap();
    compGen.writeDataFiles(samplesIQ, samplesPerChunk, txSigMap, metadataStr, outputFolder, filePrefix);


end

function nv_pairs = structToNameValuePairs(s)
    fields = fieldnames(s);
    values = struct2cell(s);
    nv_pairs = [fields'; values'];
    nv_pairs = nv_pairs(:)';
end
