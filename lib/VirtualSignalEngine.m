classdef VirtualSignalEngine < handle
    % VirtualSignalEngine is a handle type class which is the main signal
    % VirtualSignalEngine generates the RF IQ data based on the request by
    % the user. The sourceArray property contains the 'N' sources created
    % by the user where each source contains 'M' signals. It also generates
    % the IQ metadata file in two forms.
    % 1. Coarse level metadata is created by <fileName>.json and 
    % 2. Fine level metadata is created by <fileName>.metadata

    properties (SetAccess = private)
        sourceArray (:,1) atomic.Source       % Array of properties
        rxObj atomic.Rx {mustBeScalarOrEmpty} % Atomic.Rx object
    end

    % constructor
    methods
        function this = VirtualSignalEngine(sourceArray, rxObj)
        % Constructor populates the virtual signal engine parameterof
        % source array and receiver object.
        %
        % :param sourceArray: Array of sources pertaining to sigGen object
        % :type sourceArray: array[:class:`atomic.Source`]
        %
        % :param rxObj: Rx object with receiver based parameter.(Optional)
        % :type rxObj: :class:`atomic.Rx`
        %
        % :returns: handles to the object
        % :rtype: :class:`VirtualSignalEngine`

        % Instance of the VirtualSignalEngine class.
            if nargin >= 2 && ~isempty(sourceArray)
                this.sourceArray = sourceArray;
            end
            if nargin >= 3 && ~isempty(rxObj)
                this.rxObj = rxObj;
            end
        end
    end

    methods (Static)
        function out = parseMetadataForScoring(in)
            % Parses complete metadata and extracts only certain
            % parameter required for scoring.
            %
            % :param in: complete metadata recorded using the report
            % :type in: string
            %
            % :returns: scoring json output
            % :rtype: JSON object

            in = jsondecode(in);
            out = {};
            for iSource = 1:numel(in.sourceArray)
                source = in.sourceArray(iSource);
                signalSet = cell(1, numel(source.signalArray));
                for iSignal = 1:numel(source.signalArray)
                    signal = source.signalArray(iSignal);
                    if iscell(signal)
                        signal = signal{:};
                    end
                    if isfield(signal, 'wgnPowerDbm')
                        continue;
                    end
                    energySet = cell(1, numel(signal.transmissionArray));

                    for iTransmission = 1:numel(signal.transmissionArray)
                        out{end+1} = signal.transmissionArray(iTransmission);
                        out{end}.freq_lo = out{end}.freq_lo/1e6;
                        out{end}.freq_hi = out{end}.freq_hi/1e6;
                        out{end}.bandwidth_Hz = out{end}.bandwidth_Hz/1e6;
                        energySet{iTransmission} = signal.transmissionArray(iTransmission).instance_name;
                    end

                    signalStruct = signal.requiredMetadata;
                    signalStruct.reference_freq = signalStruct.reference_freq/1e6;
                    signalStruct.bandwidth_Hz = signalStruct.bandwidth_Hz/1e6;
                    signalStruct.freq_lo = signalStruct.freq_lo/1e6;
                    signalStruct.freq_hi = signalStruct.freq_hi/1e6;
                    signalStruct.energy_set = energySet;
                    out{end+1} = signalStruct;

                    signalSet{iSignal} = signalStruct.instance_name;
                end

                source = rmfield(source, {'signalArray', 'imperfectionCfg'});
                source.signal_set = signalSet;
                out{end+1} = source;
            end

            for i = 1:numel(in.rxObj)
                out{end+1} = in.rxObj(i);
                out{end}.freqCenter_Hz = out{end}.freqCenter_Hz/1e6;
                out{end}.sampleRate_Hz = out{end}.sampleRate_Hz/1e6;
            end

            temp = struct;
            temp.reports = out;
            out = jsonencode(temp, 'PrettyPrint',true);
        end

        function samplesIQ = writeDataFiles(samplesIQ, metadataJsonStr, folder, filenameBase)
            % Parses complete metadata and extracts only certain
            % parameter required for scoring.
            %
            % :param samplesIQ: Input samples to be written in IQ file.
            % :type samplesIQ: vector[complex]
            %
            % :param metadataJsonStr: Metadata in string form that needs to be encoded in json.
            % :type metadataJsonStr: string
            %
            % :param folder: Folder to which the output files are written.
            % :type folder: string
            %
            % :param filenameBase: string form of file name for output.
            % :type filenameBase: string
            %
            % :returns: scoring json output.
            % :rtype: JSON object

            if nargin < 4 || isempty(folder)
                folder =  '/tmp/scisrs_dataset/';
                filenameBase = 'default_data';
            end

            if ~exist(folder,'dir')
                mkdir(folder);
            end

            % write IQ samples data file
            if ~isempty(samplesIQ) && ~all(isnan(samplesIQ(:)))
                dataFile = fullfile(folder, filenameBase + '.32cf');
                % warning("VirtualSignalEngine Write IQ is normalizing the samples")
                warning("VirtualSignalEngine Write IQ is not normalizing the samples")
                % samplesIQ = samplesIQ / maxM(abs(samplesIQ));
                write_complex_binary(samplesIQ, dataFile);
            end
            % write to json string
            metadataFile = fullfile(folder, filenameBase + '.json');
            fid = fopen(metadataFile, 'w');
            fprintf(fid, metadataJsonStr);
            fprintf(fid,"\n");
            fclose(fid);

            % write to report for scoring
            scoringJsonStr = VirtualSignalEngine.parseMetadataForScoring(metadataJsonStr);
            scoringFile = fullfile(folder, filenameBase + '_scoring.json');
            fid = fopen(scoringFile, 'w');
            fprintf(fid, scoringJsonStr);
            fprintf(fid,"\n");
            fclose(fid);

        end
        function [samplesIQ, metadataStruct] = readDataFiles(folder, filenameBase)
        % read back the written metadata files
        %
        % :param folder: Folder in which the files are written
        % :type folder: string
        %
        % :param filenameBase: base filename which was used to store the data
        % :type filenameBase: string
        %
        % :returns: tuple of samplesIQ, metadataStruct
        % :rtype: (vector[complex], struct)
 
        
            if nargin < 2 || isempty(folder)
                folder =  "/tmp/scisrs_dataset/";
                filenameBase = "default_data";
            end

            if ~exist(folder,'dir')
                error("Folder DNE");
            end

            % write IQ samples data file
            dataFile = fullfile(folder, filenameBase + '.32cf');
            samplesIQ = read_complex_binary(dataFile);

            % write to json string
            metadataFile = fullfile(folder, filenameBase + '.json');
            fid = fopen(metadataFile, 'r');
            metadataStruct = fread(fid, '*char');
            metadataStruct = jsondecode(metadataStruct(:)');
            
        end
    end

    methods
        function addSource(this, sourceIn)
        % add a source to the virtualSignalEngine object
        %
        % :param this: Object of type virtualSignalEngine
        % :type this: :class:`VirtualSignalEngine`
        %
        % :param sourceIn: Object of atomic.Source that needs to be added
        % :type sourceIn: :class:`atomic.Source`
        %
        % :returns: None

            this.sourceArray = [this.sourceArray; sourceIn];
        end

        function addRxObj(this, rxObjIn)
        % Adds an new Rx to the virtualSigGen
        %
        % :param this: handles to the object
        % :type this:  :class:`VirtualSignalEngine`
        %
        % :param rxObjIn: Object of atomic.Rx that needs to be added
        % :type rxObjIn: :class:`atomic.Rx`
        %
        % :returns: None
         
            this.rxObj = rxObjIn;
        end

        function samplesIQ = generateSamples(this, timeStart, timeStop, isOutputSamples)
        % Generate the samples source by source
        % in the array of source, sourceArray property. 
        %
        % :param this: handle to the object
        % :type this: :class:`VirtualSignalEngine`
        %
        % :param timeStart: Start time, usually set to 0
        % :type timeStart: double
        %
        % :param timeStop: total generation time. ( not to be confused with the time stop of signals)
        % :type timeStop: double
        %
        % :param isOutputSamples: Flag to see if IQ needs to be returned. Usually True.
        % :type isOutputSamples: logical
        %
        % :returns: IQ samples
        % :rtype: vector[complex]
        
            if nargin < 4
                isOutputSamples = [];
            end

            for i = 1:numel(this.sourceArray)
                samples = this.sourceArray(i).generateSamples(timeStart, timeStop, this.rxObj, isOutputSamples);
                if i == 1
                    samplesIQ = samples;
                else
                    samplesIQ = samplesIQ + samples(1:length(samplesIQ));
                end
            end
        end

        function jsonStr = getMetadataJson(this)
            % creates a metadata json file
            %
            % :param this: handle to the object
            % :type this: :class:`VirtualSignalEngine`
            %
            % :returns: JSON string
            % :rtype: string

            jsonStr = jsonencode(this,'PrettyPrint',true);
        end

        function samplesIQ = generateMultipleDataSets(this, timeStart, timeStop, nDataSet, folder, filenameBase, isOutputIQ,writeIQ)
        % Generate multiple datasets where the samples are generated
        % source by source in the array of source, sourceArray property. 
        %
        % :param this: VirtualSignalEngine object
        % :type this: :class:`VirtualSignalEngine`
        %
        % :param timeStart: Start time, usually set to 0
        % :type timeStart: double
        %
        % :param timeStop: total generation time. ( not to be confused with the time stop of signals)
        % :type timeStop: double
        %
        % :param nDataSet: Total instances of datasets to be generated
        % :type nDataSet: int
        %
        % :param folder: Output folder in which the dataset needs to be stored
        % :type folder: string
        %
        % :param filenameBase: Output file name base string
        % :type filenameBase: string
        %
        % :param isOutputIQ: Flag to see if IQ needs to be returned. Usually True.
        % :type isOutputIQ: logical
        %
        % :param writeIQ: Flag is IQ write needs to be done. 
        % :type writeIQ: logical
        %
        % :returns: IQ samples
        % :rtype: vector[complex]

        
            arguments
                this
                timeStart
                timeStop
                nDataSet (1,1) double = 1;
                folder string {mustBeScalarOrEmpty} = [];
                filenameBase string {mustBeScalarOrEmpty}= [];
                isOutputIQ (1,1) logical = true;
                writeIQ (1,1) logical = true;
            end

            if(isempty(folder))
                folder = '/tmp/scisrs_dataset/';
            end
            if(isempty(filenameBase))
                filenameBase = 'data_' + string(convertTo(datetime, "yyyymmdd"));
            end

            for iDataSet = 1 : nDataSet
                samplesIQ = this.generateSamples(timeStart, timeStop, isOutputIQ);
                metadataJsonStr = this.getMetadataJson();
                this.writeDataFiles(samplesIQ, metadataJsonStr, folder, filenameBase+'_'+num2str(iDataSet),writeIQ);
                if nDataSet > 1
                    this.regenerateWithRandomParams();
                end
            end
        end

        function regenerateWithRandomParams(this)
            % Generates the parameter with different parameters which are randomly chosen
            %
            % :param this: handles to the object
            % :type this: :class:`VirtualSignalEngine`
            %
            % :returns: None
            %
            % .. deprecated:: UNSURE
            
            % for i = 1:numel(this.sourceArray)
            %     this.sourceArray(i).regenerateWithRandomParams;
            % end
        end
    end
end