classdef WlanNonHT80211g < atomic.Signal
    %WLAN_NONHT_80211G_ATOMIC Atomic generation class for NONHT WLAN 80211G
    %OFDM Signals
    
    properties (SetAccess = private)
        nPacket (1,1) double                    = 1;    % number of packets to transmit
        idleTime (1,1) double                   = 0;    % idle time between packets
        scramblerInitialization (1,1) double    = 93;   % scrambler initialization
        mcs (1,1) double                        = 0;    % non-HT MCS
        message (1,:)                                   % message to transmit
        cfgNonHT wlanNonHTConfig                        % wlanNonHTConfig object
        testVectorPath string = "";
    end
    
    % constructor
    methods
        function this = WlanNonHT80211g(varargin)
            % Default values for optional parameters
            defaults = struct( ...
                'nPacket', 1, ...
                'idleTime', 0, ...
                'scramblerInitialization', 93, ...
                'mcs', 0, ...
                'psduLength', 1000, ...
                'message', [], ...
                'testVectorPath', "");
            
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
            this.mcs = opts.mcs;
            this.testVectorPath = string(opts.testVectorPath);

            hasExplicitMessage = ~isempty(opts.message);
            if strlength(this.testVectorPath) > 0
                vec = load_atomic_test_vector(this.testVectorPath);
                if isfield(vec.payload, 'message_bits')
                    this.message = logical(vec.payload.message_bits(:));
                    hasExplicitMessage = true;
                end
                if isfield(vec.payload, 'scrambler_initialization')
                    this.scramblerInitialization = double(vec.payload.scrambler_initialization(1));
                end
            elseif hasExplicitMessage
                this.message = opts.message;
            else
                this.message = randi([0 1], opts.psduLength * 8,1);
            end
            if ~hasExplicitMessage
                SSID = 'RFSYNTH_BEACON'; % Network SSID
                beaconInterval = this.idleTime; % In Time units (TU)
                chNum = 52;           % Channel number, corresponds to 5260MHz

                frameBodyConfig = wlanMACManagementConfig;
                frameBodyConfig.BeaconInterval = beaconInterval;
                frameBodyConfig.SSID = SSID;
                dsElementID = 3;
                dsInformation = dec2hex(chNum, 2);
                frameBodyConfig = frameBodyConfig.addIE(dsElementID, dsInformation);

                beaconFrameConfig = wlanMACFrameConfig('FrameType', 'Beacon');
                beaconFrameConfig.ManagementConfig = frameBodyConfig;
                [beacon, mpduLength] = wlanMACFrame(beaconFrameConfig, 'OutputFormat', 'bits');
                this.message = beacon;
            else
                mpduLength = max(1, ceil(numel(this.message) / 8));
            end

            this.cfgNonHT = wlanNonHTConfig;
            this.cfgNonHT.MCS = this.mcs;
            this.cfgNonHT.PSDULength = mpduLength;
            osf = 1;
            Rs = wlanSampleRate(this.cfgNonHT, 'OversamplingFactor', osf);
            this.idleTime = 0;

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
            
            dataIQ = wlanWaveformGenerator( ...
                double(this.message(:)), ...
                this.cfgNonHT, ...
                'OversamplingFactor', 1, ...
                'IdleTime', this.idleTime, ...
                'ScramblerInitialization', this.scramblerInitialization);
        end
        
    end
end
