classdef Signal < handle & matlab.mixin.Copyable & matlab.mixin.Heterogeneous
    % Signal is the parent class of all the atomic signals that contains the common properties of each
    % signal that needs to be generated.
    
    properties (SetAccess = private)
        requiredMetadata report.Signal                      % Metadata required flag
        trafficType atomic.Traffic                          % Traffic type of signal to be generated
        txPower_db (1,1) double = nan                       % Power of the signal to be transmitted.
    end
    
    properties (SetAccess = protected)
        transmissionArray (:,1) report.Transmission         % Array of start time of each packet
        transmissionRate_Hz double {mustBeScalarOrEmpty}    % Symbol rate of the signal
        snr_db (1,1) double             = inf;              % SNR required by the signal
        centerFreq_Hz (1,1) double       = 0;               % Center frequency of the signal [Hz]
        bandwidth_Hz (1,1) double                           % Bandwidth of signal [Hz]
    end
    
    % constructor
    methods
        function this = Signal(varargin)
            % :param txPower_db: Power of the signal to be transmitted.
            % :type txPower_db: double
            % :param centerFreq_Hz: Center frequency of the signal [Hz]
            % :type centerFreq_Hz: double
            % :param bandwidth_Hz: Bandwidth of signal [Hz]
            % :type bandwidth_Hz: double
            % :param trafficType: Traffic type of signal to be generated
            % :type trafficType: :class:`atomic.Traffic`
            % :param protocol: protocol
            % :type protocol: :class:`report.Protocol`
            % :param modality: modality
            % :type modality: :class:`report.Modality`
            % :param modulation: modulation
            % :type modulation: :class:`report.Modulation`
            % :param transmissionRate_Hz: Tx baseband sample rate in Hz
            % :type transmissionRate_Hz: double
            % Default values for optional parameters
            defaults = struct( ...
                'txPower_db', 0, ...
                'centerFreq_Hz', nan, ...
                'bandwidth_Hz', nan, ...
                'trafficType', "periodic", ...
                'protocol', report.Protocol.unknown, ...
                'modality', report.Modality.unknown, ...
                'modulation', report.Modulation.unknown, ...
                'transmissionRate_Hz', nan ...
                );
            
            % Parse the optional parameters using the helper function
            [opts, ~] = parseOptions(defaults, varargin{:});
            
            
            class_name = class(this);
            instance_name = random_string(class_name);
            
            % Raise error if centerFreq_Hz or bandwidth_Hz is not provided
            assert(~isnan(opts.centerFreq_Hz), "Center frequency of the signal is not provided");
            assert(~isnan(opts.bandwidth_Hz), "Bandwidth of the signal is not provided");
            
            % If transmissionRate_Hz is not provided, set it to bandwidth_Hz
            if isnan(opts.transmissionRate_Hz)
                opts.transmissionRate_Hz = opts.bandwidth_Hz;
            end
            
            
            % Set the properties from the options
            this.requiredMetadata = report.Signal( ...
                instance_name, ...
                opts.protocol, opts.modality, opts.modulation);
            this.trafficType = opts.trafficType;
            this.bandwidth_Hz = opts.bandwidth_Hz;
            this.centerFreq_Hz = opts.centerFreq_Hz;
            this.transmissionRate_Hz = opts.transmissionRate_Hz;
            this.txPower_db = opts.txPower_db;
        end
        
    end
    
    % abstract methods require subclass implementations
    methods (Abstract, Access = public)
        samplesIQ = generateTransmission(this)
        % Generates a single transmission of the signal.
        % This is the main function that needs to be implemented by the subclasses.
        %
        % :param this: Signal object
        % :type this: atomic.Signal
        %
        % :returns: IQ samples of the signal
        % :rtype: Complex vector
    end
    
    % public methods
    methods
        function samplesIQ = generateSamples(this, timeStart, timeStop, isOutputSamples)
            % Collaborates with atomic signal functions to produce IQ samples. It initiates
            % the transmission's start time, generates transmissions, and provides metadata
            % regarding signal levels.
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :param timeStart: usually 0, the start time of the signal
            % :type timeStart: double
            %
            % :param timeStop: Total length of signal to be generated. This is
            %                  different from the time stop in :class:`VirtualSignalEngine`.
            % :type timeStop: double
            %
            % :param isOutputSamples: Flag to see if IQ needs to be produced.
            % :type isOutputSamples: bool
            %
            % :returns: IQ samples of the signal
            % :rtype: double
            
            
            if nargin < 4 || isempty(isOutputSamples)
                isOutputSamples = true;
            end
            
            % remove previous transmissions (start from 0 when this fnc is
            % called)
            this.transmissionArray = report.Transmission.empty;
            
            if isOutputSamples
                samplesIQ = zeros(round((timeStop - timeStart) * this.transmissionRate_Hz), 1);
            else
                samplesIQ = nan;
            end
            
            % get start times for all transmission
            transmissionStartTime = this.trafficType.getTransmissionTimes(timeStop, timeStart);
            assert(~isempty(transmissionStartTime), "Signal does not exist in time interval provided")
            
            transmissionStartInd = 1 + round(transmissionStartTime * this.transmissionRate_Hz);
            
            % place each transmission in overall signal
            for i = 1:numel(transmissionStartInd)
                % get transmissions of data
                samples = this.generateTransmission();
                
                if isOutputSamples
                    samples = this.scaleTxPower(samples);
                end
                
                nSamplesTransmission = numel(samples);
                transmissionTotalTime = nSamplesTransmission / this.transmissionRate_Hz;
                
                if i == numel(transmissionStartInd)
                    nSamplesFinalTransmission = numel(samplesIQ) - transmissionStartInd(i);
                    if nSamplesTransmission > nSamplesFinalTransmission
                        samples = samples(1:nSamplesFinalTransmission);
                        nSamplesTransmission = nSamplesFinalTransmission;
                    end
                end
                if isOutputSamples
                    samplesIQ(transmissionStartInd(i) + (1:nSamplesTransmission)) = samples;
                end
                
                % generate transmission metadata report
                transmissionReport = report.Transmission(...
                    transmissionStartTime(i), ...
                    transmissionStartTime(i) + transmissionTotalTime, ...
                    this.centerFreq_Hz - this.bandwidth_Hz/2, ...
                    this.centerFreq_Hz + this.bandwidth_Hz/2, ...
                    strcat(this.requiredMetadata.instance_name, ' T_', num2str(i)));
                this.transmissionArray(end+1) = transmissionReport;
            end
            
            this.requiredMetadata.setTimeFreqBox(...
                min(transmissionStartTime), ...
                max(transmissionStartTime) + transmissionTotalTime, ...
                this.centerFreq_Hz - this.bandwidth_Hz/2, ...
                this.centerFreq_Hz + this.bandwidth_Hz/2);
            
        end
        
        function samplesIQ = generateSamplesCompressed(this, timeStart, timeStop, isOutputSamples)
            % Generates a compressed IQ samples. Returns IQ samples equivalent to one energy
            % unit, used in the Polaroid infrastructure.
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :param timeStart: usually 0, the start time of the signal
            % :type timeStart: double
            %
            % :param timeStop: Total length of signal to be generated.
            %                  This is different from the time stop in :class:`VirtualSignalEngine`.
            % :type timeStop: double
            %
            % :param isOutputSamples: Flag to see if IQ needs to be produced.
            % :type isOutputSamples: bool
            %
            % :returns: IQ samples of the signal
            % :rtype: double
            
            arguments
                this
                timeStart
                timeStop
                isOutputSamples
            end
            
            if nargin < 4 || isempty(isOutputSamples)
                isOutputSamples = true;
            end
            
            % get start times for all transmission
            transmissionStartTime = this.trafficType.getTransmissionTimes(timeStop, timeStart);
            assert(~isempty(transmissionStartTime), "Signal does not exist in time interval provided")
            transmissionStartInd = 1 + round(transmissionStartTime * this.transmissionRate_Hz);
            
            this.transmissionArray(numel(transmissionStartInd),1) = report.Transmission();
            %             this.transmissionArray = report.Transmission.empty();
            
            samplesIQ = this.generateTransmission();
            samplesIQ = this.scaleTxPower(samplesIQ);
            nSamplesTransmission = numel(samplesIQ);
            transmissionTotalTime = nSamplesTransmission / this.transmissionRate_Hz;
            
            % place each transmission in overall signal
            for i = 1:numel(transmissionStartInd)
                % get transmissions of data
                % generate transmission metadata report
                transmissionReport = report.Transmission(...
                    transmissionStartTime(i), ...
                    transmissionStartTime(i) + transmissionTotalTime, ...
                    this.centerFreq_Hz - this.bandwidth_Hz/2, ...
                    this.centerFreq_Hz + this.bandwidth_Hz/2, ...
                    strcat(this.requiredMetadata.instance_name, ' T_', num2str(i)));
                
                this.transmissionArray(i) = transmissionReport;
            end
            %             toc
            
            this.requiredMetadata.setTimeFreqBox(...
                min(transmissionStartTime), ...
                max(transmissionStartTime) + transmissionTotalTime, ...
                this.centerFreq_Hz - this.bandwidth_Hz/2, ...
                this.centerFreq_Hz + this.bandwidth_Hz/2);
            
            if ~isOutputSamples
                samplesIQ = nan;
            end
            
        end
        
        function verifyFreqBounds(this, freqBounds)
            % Used to check if the signal to be generated is within the bounds
            % of the RX object created for the particular signal generation engine object.
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :param freqBounds: [Centre frequency of Rx object +/- bandwidth of Rx obj/2]
            % :type freqBounds: Array
            %
            % :returns: None
            
            thisFreqBound = [this.requiredMetadata.freq_lo this.requiredMetadata.freq_hi];
            assert(all(thisFreqBound>=freqBounds(1) & thisFreqBound<=freqBounds(2)),'Signal does not fit within specified frequency bounds.');
            
            for i = 1 : numel(this.transmissionArray)
                thisFreqBound = [this.transmissionArray(i).freq_lo  this.transmissionArray(i).freq_hi];
                assert(all(thisFreqBound>=freqBounds(1) & thisFreqBound<=freqBounds(2)),'Transmission does not fit within specified frequency bounds.');
            end
        end
        
        function setActivityType(this, activityType)
            % Sets the activity type of this signal object
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :param activityType: Activity type of the signal
            % :type activityType: string
            %
            % :returns: None
            
            this.requiredMetadata.setActivityType(activityType);
        end
        
        function clearTransmissionArray(this)
            % This function clears the transmission array of the signal
            % object. This is useful when the signal object is to be
            % re-generated with new parameters.
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :returns: None
            
            this.transmissionArray = report.Transmission.empty(0,1);
        end
        
        function this = setTxPowdBm(this, powerdBm)
            % Sets the tx power of this signal object
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :param powerdBm: Tx power in dBm
            % :type powerdBm: double
            %
            % :returns: None
            
            arguments
                this
                powerdBm (1,1) double
            end
            this.txPower_db = powerdBm;
        end
        
        % Suggestion: do not use setters
        %         function this = setCenterFreqHz(this, centerFreqHz)
        %             this.centerFreq_Hz = centerFreqHz;
        %         end
        %
        %         function this = setBandwidthHz(this, bandwidthHz)
        %             this.bandwidth_Hz = bandwidthHz;
        %         end
        
        function regenerateWithRandomParams(this)
            % This function is used to regenerate the signal object with
            % random parameters. This is useful when the signal object is
            % to be re-generated with new parameters.
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :returns: None
            %
            % .. caution::
            %
            %    **NOT CURRENTLY IMPLEMENTED**
        end
    end
    
    % protected helper methods
    methods (Access = protected)
        
        function out = addNoise(this, in, sampleRate_Hz)
            % This function adds noise to the input samples,
            % Normalizes to the in-band power by using the metadata or the
            % obw function.
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :param in: Input samples
            % :type in: Array
            %
            % :param sampleRate_Hz: Sample rate of the input samples
            % :type sampleRate_Hz: double
            %
            % :returns: Output samples with noise added
            % :rtype: Array
            
            if(this.snr_db==Inf)
                % No noise added
                out = in;
            else
                % Find input power
                input_pow_dbm = db(rms(in));
                % find occupied bandwidth
                input_obw = this.bandwidth_Hz/sampleRate_Hz;
                
                % Scale noise power to ensure snr_db inside occupied bandwidth
                noise_power_db = input_pow_dbm - 10*log10(input_obw) - this.snr_db;
                
                % Create noise samples and add to input samples
                noise_samples = wgn(size(in,1),size(in,2),...
                    noise_power_db,'complex');
                out = in + noise_samples;
            end
            
        end
        
        function out = scaleTxPower(this, in)
            % Scales the input samples to match the power level
            % specified by tx_pow_dbm
            % tx_pow_dbm = 0 leads to db(rms(output_samples)) = 0
            %             assert(~isnan(tx_pow_dbm),"tx_pow_dbm is nan");
            %
            % :param this: Signal object
            % :type this: atomic.Signal
            %
            % :param in: Input samples
            % :type in: Array
            %
            % :returns: Output samples with power scaled
            % :rtype: Array
            
            if(isnan(this.txPower_db))
                out = in;
            else
                sig_pow = (rms(in));
                tx_pow = db2mag(this.txPower_db);
                out = (tx_pow/sig_pow).*in;
            end
        end
    end
    
    methods (Static)
        
        function [varargout] = executeParameterSelect(parameterSelect,varargin)
            % Required for signal generation using the configuration file.
            % This method determines parameter selection based on the configuration
            % settings and facilitates signal generation.
            % It is invoked within the context of the atomic function.
            %
            % :param parameterSelect: Type of parameter selection to be used.
            % :type parameterSelect: String
            %
            % :param varargin: array of Parameter with each parameter being an array of values.
            % :type varargin: Array
            %
            % :returns: An array of parameters with each parameter being a single value.
            % :rtype: Array
            
            assert(any(parameterSelect == ["fuzzy","sweep","fixed"]), ...
                "Invalid name-value argument 'parameterSelect'. Value must be 'fuzzy', 'sweep', or 'fixed'")
            
            for idx = 1:length(varargin)
                
                switch parameterSelect
                    case "fuzzy"
                        varargout{idx} = datasample(varargin{idx},1);
                    case "sweep"
                        varargout{idx} = varargin{idx};
                    case "fixed"
                        varargout{idx} = varargin{idx}(1);
                end
            end
        end
    end
end