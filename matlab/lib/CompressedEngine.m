classdef CompressedEngine < VirtualSignalEngine
    % The CompressedEngine class is a virtual signal engine that generates signals
    % and writes them to a data file. The data file is then read by the
    % SDR interface and transmitted over the air.
    
    properties (SetAccess = protected)
        txVec (:,1) atomic.Tx {mustBeVector} % vector of tx radios and capabilities
        
        signalArray (:,1) atomic.Signal % Vector of signals
        
        % TODO: Have to also create an Rx Vector?
    end
    
    properties (SetAccess = private)
        numGeneratedSources uint16 = 0;
    end
    
    methods
        function this = CompressedEngine()
            % Constructor for the CompressedEngine class
            %
            % :returns: CompressedEngine Engine
            % :rtype: :class:`CompressedEngine`

            this@VirtualSignalEngine();
        end
        
        function addTxObj(this, TxObj)
            % Add a transmitter object to the CompressedEngine engine
            %
            % :param this: handle to the CompressedEngine engine
            % :type this: :class:`CompressedEngine`
            %
            % :param TxObj: handle to the transmitter object
            % :type TxObj: :class:`atomic.Tx`
            %
            % :returns: None

            this.txVec = [this.txVec; TxObj];
        end
        
        function [samplesIQ, samplesPerChunk] = generateSamplesCompressed(this, timeStart, timeStop, isOutputSamples)
            % Generate samples for the CompressedEngine engine
            %  
            % :param this: handle to the CompressedEngine engine
            % :type this: :class:`CompressedEngine`
            %
            % :param timeStart: start time of the samples
            % :type timeStart: double
            %
            % :param timeStop: stop time of the samples
            % :type timeStop: double
            %
            % :param isOutputSamples: flag to output samples
            % :type isOutputSamples: bool
            %
            % :returns: samplesIQ, samplesPerChunk
            % :rtype: double, double

            if nargin < 4
                isOutputSamples = [];
            end
            samplesIQ = [];
            samplesPerChunk = [];
            for i = 1:numel(this.sourceArray)
                [samples, numSampList] = this.sourceArray(i).generateSamplesCompressed(timeStart, timeStop, this.rxObj, isOutputSamples);
                samplesIQ = [samplesIQ;samples];
                samplesPerChunk = [samplesPerChunk;numSampList];
                fprintf("Done with Source %d\n",i);
            end
        end
        
        function this = addSignal(this, signalObj)
            % Add a signal object to the CompressedEngine engine
            %
            % :param this: handle to the CompressedEngine engine
            % :type this: :class:`CompressedEngine`
            %
            % :param signalObj: handle to the signal object
            % :type signalObj: :class:`atomic.Signal`
            %
            % :returns: handle to the CompressedEngine engine
            % :rtype: :class:`CompressedEngine`

            arguments
                this
                signalObj (:,1) atomic.Signal
            end
            this.signalArray = [this.signalArray; signalObj];
        end
        
        function [txIdVec] = mapSignalsToTxandSource(this)
            % Map signals to transmitters and initialize sources with appropriate parameters
            %
            % :param this: handle to the CompressedEngine engine
            % :type this: :class:`CompressedEngine`
            %
            % :returns: txIdVec
            % :rtype: double
            %
            % .. todo::
            %
            %   * Better signal mapping algorithm
            %   * Gain control

            % step 0: get number of Tx
            numTx = numel(this.txVec);
            assert(numTx>0, "No transmitters initialized, cannot continue");
            
            % Get max number of simultaneous signals:
            signalLims = [];
            signalLimArray = [];
            
            for sigObj = (this.signalArray).'
                signalLims = [signalLims, fixed.Interval(sigObj.trafficType.startTime,sigObj.trafficType.stopTime)];
                signalLimArray = [signalLimArray; sigObj.trafficType.startTime,sigObj.trafficType.stopTime];
            end
            
            
            numSimult = [];
            for sigId = 1:numel(this.signalArray)
                iterSimult = 0;
                for curLim = signalLims
                    intersectI = intersect(signalLims(sigId),curLim);
                    if ~isempty(intersectI)
                        iterSimult = iterSimult + 1;
                    end
                end
                numSimult = [numSimult,iterSimult];
            end
            maxSimult = max(numSimult);
            
            % step 1: get number of sources
            numSources = maxSimult;
            assert(numSources<=numTx, "Number of sources cannot be more than number of transmitters")
            
            % step 2: try to assign signals to Tx
            % Start-time-first scheduler
            
            % Sort jobs by start-time
            [signalLimArray, sigIndices] = sortrows(signalLimArray);
            
            % Initialize worker end-times
            endTimes = zeros(numTx,1);
            % Initialize source object for each Tx
            sourceObjList = [];
            for txIdx = 1:numTx
                sourceObjList = [sourceObjList, this.getSourceHelper(this.txVec(txIdx).samplingRate_Hz, this.txVec(txIdx).location)];
            end
            
            % Signal to tx assignments
            txIdVec = zeros(numel(this.signalArray),1);
            
            % Iterate over jobs
            for idx = 1:size(signalLimArray,1)
                jobTimes = signalLimArray(idx,:);
                
                % Find earliest available worker
                [earliestTime, workerId] = min(endTimes);
                assert(earliestTime <= jobTimes(1), "Failed to assign worker")
                
                % Assign worker and update worker end time
                txIdVec(sigIndices(idx)) = workerId;
                endTimes(workerId) = jobTimes(2);
                
                % Add signal to the worker's source object
                sourceObjList(workerId).addSignal(this.signalArray(sigIndices(idx)))
            end
            
            
            for srcObj = sourceObjList
                this.addSource(srcObj);
            end
            
        end
        
        function sourceObj = getSourceHelper(this, rxSampleRate_Hz, location, switchFlag)
            % Get a source object for the CompressedEngine engine
            %
            % :param this: handle to the CompressedEngine engine
            % :type this: :class:`CompressedEngine`
            %
            % :param rxSampleRate_Hz: Receiver sample rate [Hz]
            % :type rxSampleRate_Hz: double
            %
            % :param location: Location of the source
            % :type location: double
            %
            % :param switchFlag: Flag to switch between different source types
            % :type switchFlag: string
            %
            % :returns: sourceObj
            % :rtype: :class:`atomic.Source`

            arguments
                this
                rxSampleRate_Hz double
                location (1,3) double = [0 0 0]
                switchFlag string = "default"
            end
            
            instance_name = switchFlag+string(this.numGeneratedSources);
            %instance_name = switchFlag+string(randi(1000,1,1));
            this.numGeneratedSources = this.numGeneratedSources + 1;
            
            switch switchFlag
                case "default"
                    sourceObj = atomic.Source(instance_name, "default_source_device",...
                        rxSampleRate_Hz,location);
            end
        end
        
        function [txIdVec] = getSignalTxMap(this)
            % Produce a map of signal index that has to go to a particular tx index 
            %
            % :param this: handle to the CompressedEngine engine
            % :type this: :class:`CompressedEngine`
            %
            % :returns: txIdVec
            % :rtype: double
            %
            % .. todo::
            %
            %    * Better signal mapping algorithm
            %    * Gain control

            
            % step 0: get number of Tx
            numTx = numel(this.txVec);
            assert(numTx>0, "No transmitters initialized, cannot continue");
            
            % step 1: get number of sources
            % At least as many Tx as number of sources
            numSources = numel(this.sourceArray);
            assert(numSources<=numTx, "Number of sources cannot be more than number of transmitters")
            
            % step 2: try to assign signals to Tx
            txIdVec = [];
            numTxUsed = 0;
            for srcId = 1:numSources
                tempSrc = this.sourceArray(srcId);
                % 1 signal to 1 Tx association
                numSig = numel(tempSrc.signalArray);
                for sigId = 1:numSig
                    numTxUsed = numTxUsed+1;
                    assert(numTxUsed<=numTx,"Setup requires higher number of transmitter, signal mapping failed")
                    txIdVec = [txIdVec, numTxUsed];
                end
            end
        end
        
        function [] = plotSignalTimeFreq(this)
            % Plot the time-frequency plot of the signals
            %
            % :param this: handle to the CompressedEngine engine
            % :type this: :class:`CompressedEngine`
            %
            % :returns: None
                        
            
            numSig = numel(this.signalArray);
            
            for sigId = 1:numSig
                vertexX = [this.signalArray(sigId).requiredMetadata.freq_lo, this.signalArray(sigId).requiredMetadata.freq_hi,...
                    this.signalArray(sigId).requiredMetadata.freq_hi, this.signalArray(sigId).requiredMetadata.freq_lo];
                vertexX = vertexX/1e6;
                
                vertexY = [this.signalArray(sigId).requiredMetadata.time_start, this.signalArray(sigId).requiredMetadata.time_start,...
                    this.signalArray(sigId).requiredMetadata.time_stop, this.signalArray(sigId).requiredMetadata.time_stop];
                
                patch('XData',vertexX,'YData',vertexY,'FaceColor',[0.8500 0.3250 0.0980],'FaceAlpha',0.5);
                hold on;
                
                text(this.signalArray(sigId).requiredMetadata.freq_hi/1e6,...
                    this.signalArray(sigId).requiredMetadata.time_start,...
                    ["Sig."+string(sigId),string(this.signalArray(sigId).requiredMetadata.modality),...
                    string(this.signalArray(sigId).requiredMetadata.modulation)],'Interpreter','none')
            end
            hold off
            grid on;
            xlabel("Frequency (MHz)")
            ylabel("Time (s)")
            plot_magic();
            
            
        end
        
        function writeDataFiles(this, samplesIQ, samplesPerChunk, txSigMap, metadataJsonStr, folder, filenameBase)
            % Write data files for the SDR interface
            %
            % :param this: handle to the CompressedEngine engine
            % :type this: :class:`CompressedEngine`
            %
            % :param samplesIQ: Samples of the signal
            % :type samplesIQ: double
            %
            % :param samplesPerChunk: Number of samples per chunk
            % :type samplesPerChunk: double
            %
            % :param txSigMap: Tx signal map
            % :type txSigMap: double
            %
            % :param metadataJsonStr: Metadata in JSON format
            % :type metadataJsonStr: string
            %
            % :param folder: Folder to write the data files
            % :type folder: string
            %
            % :param filenameBase: Base name of the data files
            % :type filenameBase: string
            %
            % :returns: None

            if nargin < 6 || isempty(folder)
                folder =  '/tmp/scisrs_dataset/';
                filenameBase = 'default_data';
            end
            
            if ~exist(folder,'dir')
                mkdir(folder);
            end
            
            filenameVec = [];
            
            % Create metadata for SDR interface, and scoring report
            [~, instanceNameVec, energyTable, signalTable] = CompressedEngine.parseMetadataSplit(metadataJsonStr);
            scoringJsonStr = VirtualSignalEngine.parseMetadataForScoring(metadataJsonStr);
            scoringFile = fullfile(folder, string(filenameBase) + '_scoring.json');
            fid = fopen(scoringFile, 'w');
            fprintf(fid, scoringJsonStr);
            fprintf(fid,"\n");
            fclose(fid);
            
            filenameVec = [filenameVec;scoringFile];
            
            
            %             for idx = 1:numel(scoringJsonStr)
            %                 instanceName = instanceNameVec(idx);
            %                 scoringFile = fullfile(folder, filenameBase + "_" + instanceName + ".json");
            %                 fid = fopen(scoringFile, 'w');
            %                 fprintf(fid, scoringJsonStr(idx));
            %                 fprintf(fid,"\n");
            %                 fclose(fid);
            %             end
            
            % write IQ samples data file
            samplesPerChunk = [1;cumsum(samplesPerChunk)];
            iqDataFileVec = [];
            if ~isempty(samplesIQ) && ~all(isnan(samplesIQ(:)))
                for sigId = 1:numel(instanceNameVec)
                    dataFile = fullfile(folder, string(filenameBase) + "_" +string(instanceNameVec(sigId)) + '.32cf');
                    iqDataFileVec = [iqDataFileVec; string(dataFile)];
                    samplesIQWrite = samplesIQ((samplesPerChunk(sigId)+1):samplesPerChunk(sigId+1));
                    write_complex_binary(samplesIQWrite, dataFile);
                    
                    filenameVec = [filenameVec;dataFile];
                end
            end
            
            % convert signal ID to transmitter ID
            tx_radio = txSigMap(energyTable.signal_index);
            iqDataFile = iqDataFileVec(energyTable.signal_index);
            try
                energyTable.tx_radio = tx_radio.';
            catch
                energyTable.tx_radio = tx_radio;
            end
            energyTable.iq_filename = iqDataFile;
            energyMetaFile = fullfile(folder, string(filenameBase) + '_energy_meta.csv');
            writetable(energyTable, energyMetaFile);
            filenameVec = [filenameVec;energyMetaFile];
            
            signalMetaFile = fullfile(folder, string(filenameBase)+'_signal_meta.txt');
            writetable(signalTable, signalMetaFile);
            filenameVec = [filenameVec;signalMetaFile];
            
            
            % Save self as mat file:
            mat_filename = string(filenameBase) + "_compressed_obj.mat";
            save(mat_filename,'this');
            filenameVec = [filenameVec;mat_filename];
            
            zip(fullfile(folder, string(filenameBase)+".zip"),filenameVec);
            
            for filenameI = filenameVec'
                delete(filenameI);
            end
            
        end
        
        
    end
    
    methods (Access=protected)
        %             % by signal Tx mapper
        %             this.sourceArray = [this.sourceArray; sourceObj];
        %         end
    end
    
    methods (Static)
        
        
        
        
        function [jsonStrVec, instanceNameVec, energyTable, signalTable] = parseMetadataSplit(in)
            % Parse metadata for the SDR interface
            %
            % :param in: Metadata in JSON format
            % :type in: string
            %
            % :returns: jsonStrVec, instanceNameVec, energyTable, signalTable
            % :rtype: string, string, table, table

            in = jsondecode(in);
            jsonStrVec = [];
            instanceNameVec = [];
            
            energyTable = table();
            signalTable = table();
            signal_index = 1;
            for iSource = 1:numel(in.sourceArray)
                source = in.sourceArray(iSource);
                for iSignal = 1:numel(source.signalArray)
                    out = {};
                    signal = source.signalArray(iSignal);
                    % Check if signal is a cell, if so, get first element:
                    if iscell(signal)
                        signal = signal{1};
                    end

                    energySet = cell(1, numel(signal.transmissionArray));
                    
                    for iTransmission = 1:numel(signal.transmissionArray)
                        out{end+1} = signal.transmissionArray(iTransmission);
                        
                        out{end}.report_type = string(out{end}.report_type);
                        out{end}.instance_name = string(out{end}.instance_name);
                        out{end}.signal_index = signal_index;
                        out{end}.energy_index = iTransmission;
                        
                        energySet{iTransmission} = signal.transmissionArray(iTransmission).instance_name;
                        
                        if isempty(energyTable)
                            energyTable = struct2table(out{end});
                        else
                            energyTable = [energyTable;struct2table(out{end})];
                        end
                    end
                    
                    signalStruct = signal.requiredMetadata;
                    
%                     [tprMin, tprMax] = getTPRforSignal(signal,"1_SM200C");
%                     signalStruct.tprMin = tprMin;
%                     signalStruct.tprMax = tprMax;
                    
                    signalTable = [signalTable;struct2table(charvec2str(signalStruct))];
                    signalStruct.energy_set = energySet;
                    out{end+1} = signalStruct;
                    temp = struct;
                    temp.reports = out;
                    
                    jsonStr = jsonencode(temp, 'PrettyPrint',true);
                    jsonStrVec = [jsonStrVec;string(jsonStr)];
                    
                    instanceNameVec = [instanceNameVec;string(signalStruct.instance_name)];
                    signal_index = signal_index+1;
                end
            end
            
            % Sort energy table
            energyTable = sortrows(energyTable,3);
        end
        
        
        
    end
end

function struct = charvec2str(struct)
    % Convert character vector to string
    %
    % :param struct: structure to be converted
    % :type struct: structure
    %
    % :returns: struct
    % :rtype: structure

% Get a list of field names in the structure
fields = fieldnames(struct);

% Loop through each field
for i = 1:numel(fields)
    % Get the current field
    field = struct.(fields{i});
    
    % Check if the field is a character vector
    if ischar(field)
        % Convert the character vector to a string
        struct.(fields{i}) = string(field);
        % Check if the field is a structure
    elseif isstruct(field)
        struct.(fields{i}) = charvec2str(field);
    end
end
end
