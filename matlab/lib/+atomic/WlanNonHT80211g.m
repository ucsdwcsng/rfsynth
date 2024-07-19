classdef WlanNonHT80211g < atomic.Signal
    %WLAN_NONHT_80211G_ATOMIC Atomic generation class for NONHT WLAN 80211G
    %OFDM Signals
    
    properties (SetAccess = private)
        nPacket (1,1) double                    = 1;    % number of packets to transmit
        idleTime (1,1) double                   = 0;    % idle time between packets
        scramblerInitialization (1,1) double    = 93;   % scrambler initialization
        message (1,:)                                   % message to transmit
        cfgNonHT wlanNonHTConfig                        % wlanNonHTConfig object
    end
    
    % constructor
    methods
        function this = WlanNonHT80211g(varargin)
            % Default values for optional parameters
            defaults = struct( ...
                'nPacket', 1, ...
                'idleTime', 0, ...
                'scramblerInitialization', 93, ...
                'psduLength', 1000, ...
                'message', []);
            
            % Parse the optional parameters using the helper function
            [opts, unmatched] = parseOptions(defaults, varargin{:});
            
            % Add bandwdith and transmission rate to the unmatched cell
            unmatched = [unmatched, {'bandwidth_Hz', 16.8e6}, {'transmissionRate_Hz', 20e6}];
            
            % Call superclass constructor
            this@atomic.Signal(unmatched{:});
            
            % Set the properties from the options
            this.nPacket = opts.nPacket;
            this.idleTime = opts.idleTime;
            this.scramblerInitialization = opts.scramblerInitialization;

            if ~isempty(opts.message)
                this.message = opts.message;
            else
                this.message = randi([0 1], opts.psduLength,1);
            end
            
            SSID = 'RFSYNTH_BEACON'; % Network SSID
            beaconInterval = this.idleTime; % In Time units (TU)
            band = 5;             % Band, 5 or 2.4 GHz
            chNum = 52;           % Channel number, corresponds to 5260MHz
            bitsPerByte = 8;      % Number of bits in 1 byte
            
            % Create Beacon frame-body configuration object
            frameBodyConfig = wlanMACManagementConfig;
            frameBodyConfig.BeaconInterval = beaconInterval;  % Beacon Interval in Time units (TUs)
            frameBodyConfig.SSID = SSID;                      % SSID (Name of the network)
            dsElementID = 3;                                  % DS Parameter IE element ID
            dsInformation = dec2hex(chNum, 2);                % DS Parameter IE information
            frameBodyConfig = frameBodyConfig.addIE(dsElementID, dsInformation);  % Add DS Parameter IE to the configuration
            
            % Create Beacon frame configuration object
            beaconFrameConfig = wlanMACFrameConfig('FrameType', 'Beacon');
            beaconFrameConfig.ManagementConfig = frameBodyConfig;
            
            % Generate Beacon frame bits
            [beacon, mpduLength] = wlanMACFrame(beaconFrameConfig, 'OutputFormat', 'bits');
            
            % Calculate center frequency for the given band and channel number
            % fc = helperWLANChannelFrequency(chNum, band);
            
            this.cfgNonHT = wlanNonHTConfig;       % Create a wlanNonHTConfig object
            this.cfgNonHT.PSDULength = mpduLength; % PSDU length in bytes
            osf = 1;                        % Oversampling factor
            Rs = wlanSampleRate(this.cfgNonHT, 'OversamplingFactor', osf);  % Get the sampling rate
            
            this.idleTime = beaconInterval*1024e-6 * 0;
            this.message = beacon;
            
            % this.cfgNonHT.PSDULength = psduLength;
            % BW = regexp(this.cfgNonHT.ChannelBandwidth,'\d*','Match');
            this.transmissionRate_Hz = Rs;
        end
    end
    
    % public methods
    methods
        function dataIQ = generateTransmission(this)
            % Generate one single transmission of WLAN OFDM
            %
            % :returns: IQ data of the transmission
            % :rtype: vector[complex]
            
            dataIQ = wlanWaveformGenerator(this.message, this.cfgNonHT, 'OversamplingFactor', 1, 'IdleTime', this.idleTime);
        end
        
    end
end