classdef Bluetooth < atomic.Signal
    % Single bluetooth signal
    
    properties (SetAccess = private)
        message (:,1) logical                                                                                                                   % message to be transmitted
        mode char                                                       = 'LE1M';                                                               % mode of transmission
        samplesPerSymbol (1,1) double {mustBePositive, mustBeInteger}   = 8;                                                                    % samples per symbol
        channelIndex (1,1) double {mustBeInteger, mustBeNonnegative}    = 37;                                                                   % channel index
        accessAddress (32,1) logical                                    = [0 1 1 0 1 0 1 1 0 1 1 1 1 1 0 1 1 0 0 1 0 0 0 1 0 1 1 1 0 0 0 1];    % access address
        whitenStatus char                                               = 'Off';                                                               % data whitening status
        modulationIndex (1,1) double                                    = 0.5;                                                                 % GFSK modulation index
        pulseLength (1,1) double {mustBePositive, mustBeInteger}        = 1;                                                                    % Gaussian pulse length
        dfPacketType char                                               = 'Disabled';                                                          % direction finding packet type
        testVectorPath string = "";
    end
    
    % constructor
    methods
        function this = Bluetooth(varargin)
            % Default values for optional parameters
            defaults = struct( ...
                'message', [], ...
                'mode', 'LE1M', ...
                'samplesPerSymbol', 8, ...
                'channelIndex', 37, ...
                'accessAddress', [], ...
                'whitenStatus', 'Off', ...
                'modulationIndex', 0.5, ...
                'pulseLength', 1, ...
                'dfPacketType', 'Disabled', ...
                'testVectorPath', "" ...
                );
            % docstring
            % :param message: message to be transmitted
            % :type message: logical vector
            % :param mode: mode of transmission
            % :type mode: str, values = ['LE1M', 'LE2M', 'LE500K', 'LE125K']. Only LE1M supported
            % :param samplesPerSymbol: samples per symbol
            % :type samplesPerSymbol: int
            % :param channelIndex: channel index
            % :type channelIndex: int
            % :param accessAddress: access address
            % :type accessAddress: logical vector
            
            % Parse the optional parameters using the helper function
            [opts, unmatched] = parseOptions(defaults, varargin{:});
            
            % Set up constant/hardcoded parameters
            if strcmp(opts.mode, 'LE2M')
                bandwidth_Hz = 2.51e6;
                transmission_rate_hz = 2e6 * opts.samplesPerSymbol;
            else
                bandwidth_Hz = 1.255e6;
                transmission_rate_hz = 1e6 * opts.samplesPerSymbol;
            end
            
            % Call superclass constructor
            unmatched = [unmatched, {'protocol', report.Protocol.unknown}, {'modality', report.Modality.single_carrier}, {'modulation',report.Modulation.gmsk},...
                {'bandwidth_Hz', bandwidth_Hz}, {'transmissionRate_Hz', transmission_rate_hz}];
            this@atomic.Signal(unmatched{:});
            
            % Check inputs and set the properties
            assert(numel(opts.message) <= 2080, ...
                'max length of bluetooth message is 2080')
            message = opts.message;
            if isempty(message)
                message = randi([0 1],640,1);
            end
            this.message = message;
            
            assert(any(strcmp({'LE1M', 'LE2M', 'LE500K', 'LE125K'}, opts.mode)), 'not a valid mode');
            this.mode = opts.mode;
            this.samplesPerSymbol = opts.samplesPerSymbol;
            assert(opts.channelIndex >= 0 && opts.channelIndex <= 39, 'channel index must be in the range [0, 39]');
            this.channelIndex = opts.channelIndex;
            assert(any(strcmp({'On', 'Off'}, opts.whitenStatus)), 'whiten status must be On or Off');
            this.whitenStatus = opts.whitenStatus;
            assert(opts.modulationIndex >= 0.45 && opts.modulationIndex <= 0.55, 'modulation index must be in the range [0.45, 0.55]');
            this.modulationIndex = opts.modulationIndex;
            assert(opts.pulseLength >= 1 && opts.pulseLength <= 4, 'pulse length must be in the range [1, 4]');
            this.pulseLength = opts.pulseLength;
            assert(any(strcmp({'Disabled', 'ConnectionCTE', 'ConnectionlessCTE'}, opts.dfPacketType)), 'invalid DF packet type');
            this.dfPacketType = opts.dfPacketType;
            
            if ~isempty(opts.accessAddress)
                this.accessAddress = opts.accessAddress;
            end
            this.testVectorPath = string(opts.testVectorPath);
            
            
        end
        
        
    end
    
    % public methods
    methods
        function dataIQ = generateTransmission(this)
            % Generate one single transmission
            %
            % :param this: instance of the Bluetooth class
            % :type this: :class:`atomic.Bluetooth`
            %
            % :returns: IQ data
            % :rtype: complex vector
            
            message = this.message;
            accessAddress = this.accessAddress;
            if strlength(this.testVectorPath) > 0
                vec = load_atomic_test_vector(this.testVectorPath);
                if isfield(vec.payload, 'message_bits')
                    message = logical(vec.payload.message_bits(:));
                end
                if isfield(vec.payload, 'access_address_bits')
                    accessAddress = logical(vec.payload.access_address_bits(:));
                end
            end

            dataIQ = bleWaveformGenerator(message,...
                'Mode', this.mode, ...
                'ChannelIndex', this.channelIndex, ...
                'SamplesPerSymbol', this.samplesPerSymbol, ...
                'AccessAddress', accessAddress, ...
                'WhitenStatus', this.whitenStatus, ...
                'ModulationIndex', this.modulationIndex, ...
                'PulseLength', this.pulseLength, ...
                'DFPacketType', this.dfPacketType);
            
            
        end
        
        function regenerateWithRandomParams(this)
            % Randomizes atomic_sig_gen_param for variety in data set generation
            %
            % :param this: instance of the Bluetooth class
            % :type this: :class:`atomic.Bluetooth`
            %
            % :returns: None
            
            this.message = randi([0 1], randi([128 1024]),1);
            this.channelIndex = randi(39);
            this.accessAddress = randi([0 1], 32, 1);
            
            if this.requiredMetadata.activity_type == report.Activity.overt_anomaly
                this.centerFreq_Hz = randi([5e6 1.5e9], 1);
                this.bandwidth_Hz = randi([1 1e4], 1);
            end
        end
    end
    methods (Static)
        
        function [instanceName,...
                trafficType, ...
                bandwidth_Hz, ...
                centerFreq_Hz, ...
                transmissionRate_Hz, ...
                txPower_db, ...
                message, ...
                mode, ...
                samplesPerSymbol, ...
                channelIndex, ...
                accessAddress] = getParameters(instanceSelect, parameterSelect)
            % Returns the parameters of the instance specified by instanceSelect
            %
            % :param instanceSelect: name of instance
            % :type instanceSelect: str
            %
            % :param parameterSelect: name of parameter
            % :type parameterSelect: str
            %
            % :returns: parameters of the instance
            % :rtype: str, double, logical vector, int
            %
            % :raise BLE:NotImplemented: if instanceSelect is not implemented
            
            
            switch instanceSelect
                case 'advertisingIndication'
                    instanceName = 'bleAdCh37';
                    message = [1	1	1	1	0	0	1	1	1	0	0	1	0	0	1	1	1	0	0	0	1	0	1	0	0	0	1	0	0	1	0	1	1	0	0	1	1	1	0	0	0	0	1	0	0	1	0	1	0	0	1	0	0	1	1	0	1	0	0	0	1	1	0	1	1	0	0	0	0	1	1	0	0	0	0	1	1	1	0	0	0	1	0	0	0	0	1	0	1	1	0	1	0	0	0	0	1	1	1	1	1	0	1	1	0	0	1	0	0	1	0	0	0	1	0	1	0	1	0	1	0	0	0	0	1	1	0	1	1	0	0	1	0	1	1	0	1	1	0	1	1	1	0	1	1	0	1	1	0	1	1	1	1	1	0	0	0	0	0	1	1	1	1	0	0	0	1	1	1	0	1	1	1	0	0	0	1	1	1	0	0	1	1	0	0	0	0	0	1	0	0	1	1	0	1	0	1	0	0	1	0	0	1	1	0	0	1	1	1	0	1	1	0	0	1	0	1	1	1	0	1	1	1	0	1	1	1	1	1	0	0	1	1	0	1	1	1	1	1	0	1	0	0	0	0	1	0	1	0	0	0	0	0	0	0	0].';
                    mode = 'LE1M';
                    channelIndex = 37;
                    accessAddressHex = '8E89BED6';
                    accessAddressLen = 32;
                    transmissionRate_Hz = 1e6;
                    accessAddress = int2bit(hex2dec(accessAddressHex),accessAddressLen,false);
                    bandwidth_Hz = 1e6;
                    transmissionPerSec = 10;
                    centerFreq_Hz = 2402e6;
                    txPower_db = 1;
                    samplesPerSymbol = 8;
                otherwise
                    error('BLE instance :NotImplemented',"%s instanceSelect not implemented\n",instanceSelect);
            end
            
            trafficType = atomic.Traffic('periodic',"transmissionPerSec",transmissionPerSec(1));
            
        end
        
    end
end
