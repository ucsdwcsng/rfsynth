classdef WidebandThermalWgn < atomic.Signal
    % Atomic generation for Wideband thermal WGN
    %
    % Represents an instance of the Wideband Thermal White Gaussian Noise (WGN) signal generator.
    % It is used for generating wideband thermal noise signals for various applications.
    % The class provides methods and properties for generating and manipulating wideband thermal noise signals.
    
    properties (SetAccess = private)
        temperature_K (1,1) double      = 290;  % temperature [Kelvin]
        wgnPowerDbm (1,1) double                % power of the WGN [dBm]
    end
    
    % constructor
    methods
        function this = WidebandThermalWgn(varargin)
            % :param bandwidth_Hz: bandwidth of the signal [Hz]
            % :type bandwidth_Hz: double
            % :param centerFreq_Hz: center frequency of the signal [Hz]
            % :type centerFreq_Hz: double
            % :param temperature_K: temperature of the signal [Kelvin]
            % :type temperature_K: double
            % :returns: instance of the WidebandThermalWgn class
            % :rtype: :class:`atomic.WidebandThermalWgn`
            % Default values for optional parameters
            defaults = struct( ...
                'bandwidth_Hz', nan, ...
                'temperature_K', 290 ...
                );
            
            % Parse the optional parameters using the helper function
            [opts, unmatched] = parseOptions(defaults, varargin{:});
            
            wgnPower = physconst('Boltzmann') * opts.temperature_K * opts.bandwidth_Hz;
            wgnPowerDbm = 10 * log10(wgnPower) + 30;
 
            % Call superclass constructor
            trafficType = 'constant';
            unmatched = [unmatched,{'bandwidth_Hz',opts.bandwidth_Hz}, {'txPower_db', wgnPowerDbm }, {'trafficType', trafficType}];
            this@atomic.Signal(unmatched{:});
            
            this.wgnPowerDbm = wgnPowerDbm;
            % Set the properties from the options
            this.temperature_K = opts.temperature_K;
            
            
        end
        
        
    end
    
    % public methods
    methods
        function dataIQ = generateTransmission(this)
            % Generates transmission for the WidebandThermalWgn signal
            %
            % :returns: dataIQ - complex baseband representation of the signal
            % :rtype: vector[complex]
            %
            % .. caution::
            %
            %    **NOT CURRENTLY IMPLEMENTED**
        end
        
        function dataIQ = generateSamples(this, timeStart, timeStop, isOutputSamples)
            % Generates samples for the WidebandThermalWgn signal
            %
            % :param timeStart: start time of the signal [sec]
            % :type timeStart: double
            %
            % :param timeStop: stop time of the signal [sec]
            % :type timeStop: double
            %
            % :param isOutputSamples: flag to output samples
            % :type isOutputSamples: bool
            %
            % :returns: dataIQ - complex baseband representation of the signal
            % :rtype: vector[complex]
            
            
            if nargin < 4 || isOutputSamples
                isOutputSamples = true;
            end
            
            this.transmissionArray = report.Transmission.empty;
            
            if isOutputSamples
                nSamples = round((timeStop - timeStart) * this.transmissionRate_Hz);
                dataIQ = wgn(nSamples, 1, this.wgnPowerDbm,'complex');
                % Normalizing power:
                dataIQ = this.scaleTxPower(dataIQ);
                % Adding noise
                dataIQ = this.addNoise(dataIQ, this.transmissionRate_Hz);
            else
                dataIQ = nan;
            end
            
            % TODO: integrate tx signal to get receiver data
            %             dataIQ = dataIQ + Resample.quick(dataIQ, txSampleRate_Hz / this.rx.sampleRate_Hz);
            
            % generate transmission metadata report
            transmissionReport = report.Transmission(...
                timeStart, ...
                timeStop, ...
                this.centerFreq_Hz - this.bandwidth_Hz/2, ...
                this.centerFreq_Hz + this.bandwidth_Hz/2, ...
                strcat(this.requiredMetadata.instance_name, ' T_1'));
            this.transmissionArray(end+1) = transmissionReport;
            
            this.requiredMetadata.setTimeFreqBox(...
                timeStart, ...
                timeStop, ...
                this.centerFreq_Hz - this.bandwidth_Hz/2, ...
                this.centerFreq_Hz + this.bandwidth_Hz/2);
        end
        
        
        function txPowdBmVec = getTxPowVecFromEsNo(this, signalObj, EsNo)
            % Gets required Tx powers in dBm corresponding to each entry in EsNo for the input signalObj
            %
            % :param signalObj: signal object
            % :type signalObj: :class:`atomic.Signal`
            %
            % :param EsNo: required EsNo values
            % :type EsNo: vector
            %
            % :returns: txPowdBmVec - required Tx powers in dBm
            % :rtype: vector
            
            signalBW = signalObj.bandwidth_Hz;
            inBandNoisePow = db2pow(this.wgnPowerDbm).*signalBW./this.bandwidth_Hz;
            inBandNoisePowdBm = 10*log10(inBandNoisePow);
            
            txPowdBmVec = EsNo + inBandNoisePowdBm;
            
        end
        
    end
    
end

