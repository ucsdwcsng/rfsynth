classdef Source < handle% constant for metadata type id
    % Atomic.Source consists of properties that encapsulates a source with
    % multiple signals in it. The source models the RF chain and
    % imperfections are added post the signal generation.
    
    properties (Constant)
        report_type = "source";                 % Constant for metadata type id
    end
    
    % required inputs
    properties (SetAccess = private)
        device_origin string                    % Device origin
        instance_name string                    % Unique instance identifier
    end
    
    % optional inputs
    properties (SetAccess = private)
        signalArray (:,1) atomic.Signal         % Array of signals
    end
    
    properties (SetAccess = private)
        tx atomic.Tx {mustBeScalarOrEmpty}      % Defines physical tx params
        locationXYZ_m (1,3)                     % Location of the source
        outputSamplingRate_Hz (1,1) double      % Final sample rate of the source
        channelModel string                     % Channel model selector
        
        imperfectionCfg atomic.RFImperfections  % Defines the imperfections
    end
    
    properties (Dependent)
        nSignal (1,1)                           % Number of signals in the source
    end
    
    % constructor
    methods
        function this = Source(instance_name, device_origin, outputSamplingRate_Hz, locationXYZ_m, channelModel, imperfectionCfg)
            % Constructor of source populates the instance of the source,
            % location, final sample rate which needs to be used for
            % resampling all the signals and imperfections configuration
            % that needs to be added to the signals generated.
            %
            % :param instance_name: Unique instance identifier
            % :type instance_name: str
            %
            % :param device_origin: Device origin
            % :type device_origin: str
            %
            % :param outputSamplingRate_Hz: Final sample rate of the source
            % :type outputSamplingRate_Hz: double
            %
            % :param locationXYZ_m: Location of the source
            % :type locationXYZ_m: double
            %
            % :param channelModel: Channel model selector
            % :type channelModel: str
            %
            % :param imperfectionCfg: Defines the imperfections
            % :type imperfectionCfg: atomic.RFImperfections
            %
            % :return: instance of the source
            % :rtype: :class:`atomic.Source`
            
            
            this.instance_name = instance_name;
            this.device_origin = device_origin;
            this.outputSamplingRate_Hz = outputSamplingRate_Hz;
            this.locationXYZ_m = locationXYZ_m;
            
            if(nargin>4)
                this.channelModel = channelModel;
            else
                this.channelModel = "IDENTITY";
            end
            
            if(nargin>5)
                this.imperfectionCfg = imperfectionCfg;
            else
                this.imperfectionCfg = atomic.RFImperfections();
            end
            
        end
    end
    
    methods
        function dataIQ = generateSamples(this, timeStart, timeEnd, rx, isOutputSamples)
            % Generates the samples for the source. The samples are
            % generated for the time range specified and the rx object is
            % used to apply the channel model and the non-idealities.
            %
            % :param timeStart: Start time of the samples
            % :type timeStart: double
            %
            % :param timeEnd: End time of the samples
            % :type timeEnd: double
            %
            % :param rx: Rx object
            % :type rx: :class:`atomic.Rx`
            %
            % :param isOutputSamples: Flag to indicate if the samples need to be generated or not
            % :type isOutputSamples: bool
            %
            % :return: IQ samples
            % :rtype: vector[complex]
            
            
            if nargin < 5 || isempty(isOutputSamples)
                isOutputSamples = true;
            end
            
            if isOutputSamples
                dataIQ = zeros((timeEnd - timeStart) * this.outputSamplingRate_Hz, 1);
            else
                dataIQ = nan;
            end
            
            for i = 1:this.nSignal
                signalI = this.signalArray(i);
                data = signalI.generateSamples(timeStart, ...
                    timeEnd, isOutputSamples);
                
                if isOutputSamples
                    
                    data = this.applyNonIdealTformtoTx(data, signalI); % First non-idealities
                    data = this.applyChanneltoSignal(data, signalI, rx); % Then channel
                    [P,Q] = rat(this.outputSamplingRate_Hz/signalI.transmissionRate_Hz);
                    data = resample(data, P, Q);
                    
                    delf = -(rx.freqCenter_Hz - signalI.centerFreq_Hz)./this.outputSamplingRate_Hz;
                    numel_samples_iter = numel(data);
                    % verifyFreqBounds asserts if any signal/transmission goes
                    % out of the frequency bounds of the engine
                    signalI.verifyFreqBounds(rx.freqCenter_Hz + [-rx.sampleRate_Hz/2  rx.sampleRate_Hz/2]);
                    
                    % add rx props to metadata
                    signalI.requiredMetadata.setRxProps(rx.freqCenter_Hz, rx.sampleRate_Hz, -5);
                    
                    % TODO: Check if exp(2j*pi*n) is stable for large values of n
                    data = data.*exp(2j*pi*delf*(0:(numel_samples_iter-1)).');
                    if numel(dataIQ) > numel(data)
                        dataIQ(1:numel(data)) = dataIQ(1:numel(data)) + data;
                    else
                        dataIQ = dataIQ + data(1:numel(dataIQ));
                    end
                end
            end
        end
        
        function [dataIQ, samplesPerChunk] = generateSamplesCompressed(this, timeStart, timeEnd, rx, isOutputSamples)
            % Generates the samples for the source. The samples are
            % generated for the time range specified and the rx object is
            % used to apply the channel model and the non-idealities.
            %
            % :param timeStart: Start time of the samples
            % :type timeStart: double
            %
            % :param timeEnd: End time of the samples
            % :type timeEnd: double
            %
            % :param rx: Rx object
            % :type rx: :class:`atomic.Rx`
            %
            % :param isOutputSamples: Flag to indicate if the samples need to be generated or not
            % :type isOutputSamples: bool
            %
            % :return: IQ samples
            % :rtype: vector[complex]
            
            
            if nargin < 5 || isempty(isOutputSamples)
                isOutputSamples = true;
            end
            
            dataIQ = [];
            samplesPerChunk = [];
            for i = 1:this.nSignal
                signalI = this.signalArray(i);
                data = signalI.generateSamplesCompressed(timeStart, ...
                    timeEnd, isOutputSamples);
                
                if isOutputSamples
                    data = this.applyNonIdealTformtoTx(data, signalI); % First non-idealities
                    data = this.applyChanneltoSignal(data, signalI, rx); % Then channel
                    [P,Q] = rat(this.outputSamplingRate_Hz/signalI.transmissionRate_Hz);
                    data = resample(data, P, Q);
                    delf = -(rx.freqCenter_Hz - signalI.centerFreq_Hz)./this.outputSamplingRate_Hz;
                    numel_samples_iter = numel(data);
                    % verifyFreqBounds asserts if any signal/transmission goes
                    % out of the frequency bounds of the engine
                    signalI.verifyFreqBounds(rx.freqCenter_Hz + [-rx.sampleRate_Hz/2  rx.sampleRate_Hz/2]);
                    
                    % add rx props to metadata
                    signalI.requiredMetadata.setRxProps(rx.freqCenter_Hz, rx.sampleRate_Hz, -5);
                    
                    dataIQ = [dataIQ;data];
                    samplesPerChunk = [samplesPerChunk;numel(data)];
                end
            end
            
            if ~isOutputSamples
                dataIQ = nan;
            end
        end
        
        function addSignal(this, signal)
            % Add a signal to the source
            %
            % :param signal: Signal object
            % :type signal: :class:`atomic.Signal`
            %
            % :return: None
            
            
            this.signalArray = [this.signalArray; signal];
        end
        
        function removeSignal(this, index)
            % Remove a signal from the source
            %
            % :param index: Index of the signal to be removed
            % :type index: int
            %
            % :return: None
            
            
            arguments
                this atomic.Source
                index (1,1) {mustBeInteger, mustBePositive}
            end
            assert(index <= numel(this.signalArray), 'signal index out of bound');
            this.signalArray = [this.signalArray(1:index-1); this.signalArray(index+1:end)];
        end
        
        function regenerateWithRandomParams(this)
            %  Used to generate large random datasets.
            %
            % :param this: Source object
            % :type this: :class:`atomic.Source`
            %
            % :return: None
            
            
            % Randomize non-idealities (not a handle class)
            this.imperfectionCfg = this.imperfectionCfg.regenerateWithRandomParams();
            
            % Loop through every signal and regenerate
            for i = 1:numel(this.signalArray)
                this.signalArray(i).regenerateWithRandomParams;
                this.signalArray(i).clearTransmissionArray();
            end
        end
        
        function [num_tx_array] = getNumTransmissions(this)
            % Returns an array of transmissions per
            % signal. If the number of signals associated with this source
            % is N, then this function returns an Nx1 array of the number of
            % transmissions per signal.
            %
            % :param this: Source object
            % :type this: :class:`atomic.Source`
            %
            % :return: Array of number of transmissions per signal
            % :rtype: vector[int]
            
            
            numSig = numel(this.signalArray);
            num_tx_array = zeros(numSig,1);
            for i = 1:numSig
                num_tx_array(i) = numel(this.signalArray(i).transmissionArray);
            end
            
        end
    end
    
    % protected helper methods
    methods (Access = protected)
        function data_in = applyNonIdealTformtoTx(this, data_in, signal_obj)
            % Adds all non-idealities to the input signal and passes to output
            %
            % :param data_in: Input signal
            % :type data_in: vector[complex]
            %
            % :param signal_obj: Signal object
            % :type signal_obj: :class:`atomic.Signal`
            %
            % :return: Output signal
            % :rtype: vector[complex]
            
            data_in = this.applyIQImbaltoSignal(data_in);
            data_in = this.applyDCtoSignal(data_in, signal_obj);
            data_in = this.applyCFOtoSignal(data_in, signal_obj);
        end
        
        function data_in = applyIQImbaltoSignal(this, data_in)
            % Applies IQ imbalance to the input signal
            % based on the input phase and amplitude unbalance.
            %
            % :param data_in: Input signal
            % :type data_in: vector[complex]
            %
            % :return: Output signal
            % :rtype: vector[complex]
            
            
            thetaHalf = this.imperfectionCfg.imbalIQ(2)/2;
            epsilon = this.imperfectionCfg.imbalIQ(1);
            etaAlpha = cos(thetaHalf) + 1j*epsilon*sin(thetaHalf);
            etaBeta = epsilon*cos(thetaHalf) - 1j*sin(thetaHalf);
            
            data_in = etaAlpha.*data_in + etaBeta.*conj(data_in);
            
        end
        
        function data_in = applyDCtoSignal(this, data_in, signal_obj)
            % Applies DC offset to the input signal based on
            % input DC offset parameters.
            %
            % **TODO:** add DC offset only when signal is present
            %
            % :param data_in: Input signal
            % :type data_in: vector[complex]
            %
            % :param signal_obj: Signal object
            % :type signal_obj: :class:`atomic.Signal`
            %
            % :return: Output signal
            % :rtype: vector[complex]
            
            
            if(this.imperfectionCfg.offsetDC(1)>0)
                
                for idx = 1:length(signal_obj.transmissionArray)
                    time_start = signal_obj.transmissionArray(idx).time_start;
                    time_stop = signal_obj.transmissionArray(idx).time_stop;
                    
                    sampleStartStop = round([time_start time_stop]*signal_obj.transmissionRate_Hz) + 1;
                    
                    try
                        data_in(sampleStartStop(1):sampleStartStop(2)) = data_in(sampleStartStop(1):sampleStartStop(2)) + ...
                            this.imperfectionCfg.offsetDC(1)*exp(1j*this.imperfectionCfg.offsetDC(2))*db2mag(signal_obj.txPower_db);
                    catch
                        % This scenario occurs when there are energy bursts
                        % that are cut off by the requested signal length
                        break
                    end
                    
                end
                
            end
        end
        
        function data_in = applyCFOtoSignal(this, data_in, signal_obj)
            % Applies a CFO to input signal based on the
            % oscillator ppm tolerance.
            %
            % **TODO:** Random walk modeling of oscillator offset
            %
            % :param data_in: Input signal
            % :type data_in: vector[complex]
            %
            % :param signal_obj: Signal object
            % :type signal_obj: :class:`atomic.Signal`
            %
            % :return: Output signal
            % :rtype: vector[complex]
            
            
            if(this.imperfectionCfg.freqOffset>0)
                % pick a CFO
                freqOffsetHz = this.imperfectionCfg.freqOffset;
                
                signalLength = numel(data_in);
                phaseMultVec = exp(2j*pi*freqOffsetHz/signal_obj.transmissionRate_Hz.*(0:(signalLength-1))).';
                
                data_in = data_in.*phaseMultVec;
            end
        end
        
        
        
        function data_in = applyChanneltoSignal(this, data_in, signal_obj, rx)
            % Takes input signal, the signal object and
            % the rx object and transforms the input signal through the
            % channel described by the channelModel property.
            %
            % :param data_in: Input signal
            % :type data_in: vector[complex]
            %
            % :param signal_obj: Signal object
            % :type signal_obj: :class:`atomic.Signal`
            %
            % :param rx: Receiver object
            % :type rx: :class:`atomic.Receiver`
            %
            % :return: Output signal
            % :rtype: vector[complex]
            
            switch this.channelModel
                case "IDENTITY"
                    % No channel. Output = Input;
                    1;
                case "FSPL"
                    % Free Space Path Loss
                    % Calculate distance
                    pathLength = norm(rx.location - this.locationXYZ_m);
                    % Calculate FSPL
                    pathLoss = fspl(pathLength, 3e8/signal_obj.centerFreq_Hz);
                    % Mutliply with signal
                    data_in = data_in.*db2mag(-pathLoss);
                    
                case "WINNER2NORM"
                    % Winner2 Model - Normalized channel (no path loss)
                    required_samp_rate = signal_obj.transmissionRate_Hz;
                    [cfgModel,cfgLayout] = atomic.Source.getDefaultWINNER2Cfg(rx.location, this.locationXYZ_m, required_samp_rate,...
                        signal_obj.centerFreq_Hz, 'no');
                    [data_in] = atomic.Source.WINNER2FiltWrap(data_in, cfgModel,cfgLayout);
                    
                case "WINNER2FSPL"
                    % Winner2 Model with FSPL in built
                    required_samp_rate = signal_obj.transmissionRate_Hz;
                    [cfgModel,cfgLayout] = atomic.Source.getDefaultWINNER2Cfg(rx.location, this.locationXYZ_m, required_samp_rate,...
                        signal_obj.centerFreq_Hz, 'yes');
                    [data_in] = atomic.Source.WINNER2FiltWrap(data_in, cfgModel,cfgLayout);
                    
                case "RICIANNORM"
                    % Rician Model with Heuristic parameter init
                    % Power is normalized.
                    reqCenterFreq = signal_obj.centerFreq_Hz;
                    reqSampleRate = signal_obj.transmissionRate_Hz;
                    [dlyValues,gainValues,~] = atomic.Source.getDefaultHeuristicChannelInit(reqCenterFreq);
                    
                    % Rician
                    gainValues = abs(gainValues);
                    ricianchan = comm.RicianChannel( ...
                        'SampleRate',reqSampleRate, ...
                        'PathDelays',dlyValues, ...
                        'AveragePathGains',gainValues, ...
                        'KFactor',2.8, ...
                        'DirectPathDopplerShift',0.0, ...
                        'DirectPathInitialPhase',0.5, ...
                        'MaximumDopplerShift',50, ...
                        'DopplerSpectrum',doppler('Bell', 8), ...
                        'PathGainsOutputPort',false);
                    [data_in] = ricianchan(data_in);
                    
                case "HEURISTICNORM"
                    % Heuristic channel model with convolution for fast
                    % performance.
                    reqCenterFreq = signal_obj.centerFreq_Hz;
                    reqSampleRate = signal_obj.transmissionRate_Hz;
                    [dlyValues,gainValues,delaySpread] = atomic.Source.getDefaultHeuristicChannelInit(reqCenterFreq);
                    
                    numSampReq = 10*ceil(delaySpread*reqSampleRate);
                    deltaSequence = [1; zeros(numSampReq-1,1)];
                    
                    convKernel = zeros(numSampReq,1);
                    
                    for idx = 1:length(dlyValues)
                        dlyDelta = delayseq(deltaSequence, dlyValues(idx),...
                            reqSampleRate);
                        convKernel = convKernel + dlyDelta.*gainValues(idx);
                    end
                    
                    % Normalize kernel
                    convKernel = convKernel./norm(convKernel);
                    
                    % Filter
                    data_in = conv(data_in,convKernel,'same');
                    
                    
                otherwise
                    error("Unknown channel Model")
                    
            end
        end
        
    end
    
    methods (Static)
        function [cfgModel,cfgLayout] = getDefaultWINNER2Cfg(rxLocation, sourceLocation, required_samp_rate, centerFreq_Hz, PathLossModelUsed)
            % An easy way to generate reasonable WINNER2 channel parameter config.
            %
            % :param rxLocation: Receiver location
            % :type rxLocation: vector[double]
            %
            % :param sourceLocation: Source location
            % :type sourceLocation: vector[double]
            %
            % :param required_samp_rate: Required sample rate
            % :type required_samp_rate: double
            %
            % :param centerFreq_Hz: Center frequency
            % :type centerFreq_Hz: double
            %
            % :param PathLossModelUsed: Path loss model used
            % :type PathLossModelUsed: string
            %
            % :return: Channel model and layout
            % :rtype: :class:`atomic.wimparset` and :class:`atomic.layoutparset`
            
            if nargin < 5
                PathLossModelUsed = 'no';
            end
            
            BSAA = winner2.AntennaArray; % Isotropic
            MSAA1 = winner2.AntennaArray;
            
            MSIdx = [2]; BSIdx = {1}; NL = 1;
            rmax = 30; % 3 meter radius
            cfgLayout = winner2.layoutparset(MSIdx, BSIdx, NL, [BSAA, MSAA1],rmax);
            
            cfgLayout.Stations(2).Velocity = cfgLayout.Stations(2).Velocity/8; % approx 15 cm per second
            stationVelo = norm(cfgLayout.Stations(2).Velocity);
            cfgLayout.Pairing = [1;2];
            cfgLayout.Stations(1).Pos = rxLocation.'; % Row to column
            cfgLayout.Stations(2).Pos = sourceLocation.';
            cfgLayout.ScenarioVector = [1]; % Indoor channel model
            
            cfgModel = winner2.wimparset;
            cfgModel.NumTimeSamples = 8192;
            cfgModel.CenterFrequency = centerFreq_Hz;
            cfgModel.UseManualPropCondition = 'no';
            cfgModel.UniformTimeSampling = 'yes';
            cfgModel.PathLossModelUsed = PathLossModelUsed;
            
            cfgModel.SampleDensity = round(required_samp_rate/stationVelo*(2.99792458e8/cfgModel.CenterFrequency/2));
            cfgModel.DelaySamplingInterval  = 0;
        end
        
        function [data_in] = WINNER2FiltWrap(data_in, cfgModel,cfgLayout)
            % WINNER2FiltWrap wrapper function to buffer input signal and
            % filter it using the WINNER2 Channel Model
            %
            % :param data_in: Input signal
            % :type data_in: vector[double]
            %
            % :param cfgModel: Channel model
            % :type cfgModel: :class:`atomic.wimparset`
            %
            % :param cfgLayout: Channel layout
            % :type cfgLayout: :class:`atomic.layoutparset`
            %
            % :return: Filtered signal
            % :rtype: vector[double]
            
            WINNERChan = comm.WINNER2Channel(cfgModel, cfgLayout);
            WINNERChan.release();
            WINNERChan.reset();
            
            sizeDataIn = numel(data_in);
            data_in = buffer(data_in,cfgModel.NumTimeSamples);
            
            for idx = 1:size(data_in,2)
                [Y, ~] = WINNERChan({data_in(:,idx)});
                data_in(:,idx) = Y{1};
            end
            
            data_in = reshape(data_in,[],1);
            data_in = data_in(1:sizeDataIn);
            
            clear WINNERChan;
        end
        
        function [dlyValues,gainValues,delaySpread] = getDefaultHeuristicChannelInit(reqCenterFreq)
            % Initializes channel delay values and gains based on super cool heuristics :)
            %
            % :param reqCenterFreq: Required center frequency
            % :type reqCenterFreq: double
            %
            % :return: Delay values, gain values and delay spread
            % :rtype: vector[double], vector[double], double
            
            
            num_taps = round(7*(2.45e9/reqCenterFreq));
            delaySpread = 90e-9 * (2.45e9/reqCenterFreq).^2;
            
            dlyValues = rand(1,num_taps)*delaySpread;
            dlyValues = sort(dlyValues);
            
            % God Line: Heuristic delay getter.
            dly2gainmap = @(dlyValues, delaySpread) exp(2j*pi*rand(size(dlyValues))).*normrnd(1-dlyValues./delaySpread,0.5.*ones(size(dlyValues)));
            
            gainValues = dly2gainmap(dlyValues,delaySpread);
            
        end
        
    end
    
    % getters
    methods
        function out = get.nSignal(this)
            % Get number of signals
            %
            % :return: Number of signals
            % :rtype: int
            
            out = numel(this.signalArray);
        end
    end
end