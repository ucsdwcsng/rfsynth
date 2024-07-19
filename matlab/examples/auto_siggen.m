function auto_siggen(filename)
    % Read TAML file
    config = yaml.loadFile(filename,"ConvertToArray", true);

    % Generation parameters
    flagOutputIqSamples = config.generationParameters.flagOutputIqSamples;
    tot_time = config.generationParameters.tot_time;
    outputFile = config.generationParameters.outputFile;

    % Rx configuration
    rx = atomic.Rx(config.rxConfig.name, config.rxConfig.rxSampleRate_Hz, config.rxConfig.centerFreq_Hz, config.rxConfig.location);

    % Instantiate engine
    sigGen = VirtualSignalEngine();
    sigGen.addRxObj(rx);

    % Loop through signals and add them to sources
    signals = config.signals;
    for i = 1:length(signals)
        signal = signals(i);
%         signalArgs = structToVarargin(signal.args);
        signalArgs = namedargs2cell(signal.args);
        signalObj = feval(char("atomic."+signal.type), signalArgs{:});

        % Create a new source for each signal with default parameters
        sourceName = ['Source', num2str(i)];
        sourceOrigin = 'thematrix';
        sourceLoc = [0,0,0];% (2 * rand(1, 3) - 1) * 10; % Random location
        sourceFreqOffset = 0; % 1000 * (2 * rand - 1);
        imperfectionCfg = atomic.RFImperfections(sourceFreqOffset);

        sourceObj = atomic.Source(sourceName, sourceOrigin, config.rxConfig.rxSampleRate_Hz, sourceLoc, "IDENTITY", imperfectionCfg);
        sourceObj.addSignal(signalObj);

        sigGen.addSource(sourceObj); 
    end

    % Generate samples
    samplesIQ = sigGen.generateSamples(0, tot_time, flagOutputIqSamples);
    metadataStr = sigGen.getMetadataJson();

    % Save engine outputs
    sigGen.writeDataFiles(samplesIQ, metadataStr, outputFile);

    % Read things back
    [readSamplesIQ, readMetadataStruct] = VirtualSignalEngine.readDataFiles(outputFile);

    % Access the bounding box for the first BLE signal
    timeFreqBox = readMetadataStruct.sourceArray(2).signalArray.transmissionArray(1);
    disp(timeFreqBox)

    % Plot results
    p = PlotSignalHelper();
    p.sampleFreq_Hz = config.rxConfig.rxSampleRate_Hz;
    p.isUseTimeScale = true;
    p.plotSignal(samplesIQ, sigGen);
end

function out = structToVarargin(s)
    fields = fieldnames(s);
    out = reshape([fields'; struct2cell(s)'], 1, []);
end
