classdef Bluetooth < atomic.Signal
    % Single bluetooth signal
    
    properties (SetAccess = private)
        message (:,1) logical                                                                                                                   % message to be transmitted
        mode char                                                       = 'LE1M';                                                               % mode of transmission
        samplesPerSymbol (1,1) double {mustBePositive, mustBeInteger}   = 8;                                                                    % samples per symbol
        channelIndex (1,1) double {mustBeInteger, mustBeNonnegative}    = 37;                                                                   % channel index
        accessAddress (32,1) logical                                    = [0 1 1 0 1 0 1 1 0 1 1 1 1 1 0 1 1 0 0 1 0 0 0 1 0 1 1 1 0 0 0 1];    % access address
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
                'accessAddress', [] ...
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
            bandwidth_Hz = 1.255e6;
            transmission_rate_hz = 1e6 * opts.samplesPerSymbol;
            
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
            assert(any(strcmp({'LE1M'}, opts.mode)), 'not a valid mode');
            this.mode = opts.mode;
            this.samplesPerSymbol = opts.samplesPerSymbol;
            assert(opts.channelIndex >= 0 && opts.channelIndex <= 39, 'channel index must be in the range [0, 39]');
            this.channelIndex = opts.channelIndex;
            
            if ~isempty(opts.accessAddress)
                this.accessAddress = opts.accessAddress;
            end
            
            
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
            
            dataIQ = bleWaveformGenerator(this.message,...
                'Mode', this.mode, ...
                'ChannelIndex', this.channelIndex, ...
                'SamplesPerSymbol', this.samplesPerSymbol, ...
                'AccessAddress', this.accessAddress, ...
                'WhitenStatus', 'Off');
            
            
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
