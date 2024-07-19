classdef Signal < handle
    % Signal class for storing signal metadata

    % constant for metadata type id
    properties (Constant)
        report_type = "signal";                                                 % metadata type id
    end

    % required inputs at construction
    properties (SetAccess = private)
        % unique identifier
        instance_name string                                                    % unique instance identifier
        
        % category types
        protocol report.Protocol                                                % protocol 
        modality report.Modality                                                % modality
        modulation report.Modulation                                            % modulation 
        activity_type report.Activity = report.Activity.overt_baseline;         % activity 
    end
    
    % properties to be set when actual signal is sampled
    properties (SetAccess = private)
        time_start (1,1) double                                                 % signal start time [s]
        time_stop (1,1) double                                                  % signal stop time [s]
        freq_lo (1,1) double                                                    % signal low frequency [Hz]
        freq_hi (1,1) double                                                    % signal high frequency [Hz]

        rx_center_freq (1,1)                                                    % receiver center frequency [Hz]
        rx_sample_rate (1,1)                                                    % receiver sample rate [Hz]
        rx_input_snr (1,1) 
    end
    
    properties (Dependent)
        reference_time (1,1) double                                             % reference time
        reference_freq (1,1) double                                             % reference frequency
        
        % others
        timeLength_s (1,1) double                                               % time length [s]
        bandwidth_Hz (1,1) double                                               % bandwidth [Hz]
    end
    
    % constructor
    methods
        function this = Signal(instance_name, protocol, modality, modulation, activity)
            % Constructor for Signal class
            %
            % :param instance_name: unique instance identifier
            % :type instance_name: string
            %
            % :param protocol: protocol
            % :type protocol: :class:`report.Protocol`
            %
            % :param modality: modality
            % :type modality: :class:`report.Modality`
            %
            % :param modulation: modulation
            % :type modulation: :class:`report.Modulation`
            %
            % :param activity: activity
            % :type activity: :class:`report.Activity`
            %
            % :returns: handle to signal
            % :rtype: :class:`report.Signal`

            this.instance_name = instance_name;
            this.protocol = protocol;
            this.modality = modality;
            this.modulation = modulation;
            
            if nargin >= 5 && ~isempty(activity)
                this.activity_type = activity;
            end
        end
    end
    
    % public methods
    methods
        function setTimeFreqBox(this, time_start, time_stop, freq_lo, freq_hi)
            % Set time and frequency box
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :param time_start: start time
            % :type time_start: double
            %
            % :param time_stop: stop time
            % :type time_stop: double
            %
            % :param freq_lo: low frequency
            % :type freq_lo: double
            %
            % :param freq_hi: high frequency
            % :type freq_hi: double
            %
            % :returns: None

            this.time_start = time_start;
            this.time_stop = time_stop;
            this.freq_lo = freq_lo;
            this.freq_hi = freq_hi;
        end

        function setRxProps(this, rxCenterFreq_Hz, rxSampleRateHz, rxInputSnr)
            % Set receiver properties
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :param rxCenterFreq_Hz: Receiver center frequency
            % :type rxCenterFreq_Hz: double
            %
            % :param rxSampleRateHz: Receiver sample rate
            % :type rxSampleRateHz: double
            %
            % :param rxInputSnr: Receiver input SNR
            % :type rxInputSnr: double
            %
            % :returns: None

            this.rx_center_freq = struct("rx1",  rxCenterFreq_Hz);
            this.rx_sample_rate = struct("rx1",  rxSampleRateHz);
            this.rx_input_snr = struct("rx1",  rxInputSnr);
        end

        function updateModality(this, modalityType)
            % Update modality
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :param modalityType: modality
            % :type modalityType: :class:`report.Modality`
            %
            % :returns: None
    
            this.modality = modalityType;
        end

        function setModulation(this, modulationType)
            % Set modulation
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :param modulationType: modulation
            % :type modulationType: :class:`report.Modulation`
            %
            % :returns: None

            this.modulation = modulationType;
        end
        
        function setActivityType(this, activityType)
            % Set activity type
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :param activityType: activity
            % :type activityType: :class:`report.Activity`
            %
            % :returns: None

            this.activity_type = activityType;
        end

    end
    
    % getters
    methods
        function out = get.reference_time(this)
            % Get reference time
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :returns: reference time
            % :rtype: double

            out = mean([this.time_start, this.time_stop]);
        end

        function out = get.reference_freq(this)
            % Get reference frequency
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :returns: reference frequency
            % :rtype: double
            
            out = mean([this.freq_hi, this.freq_lo]);
        end

        function out = get.timeLength_s(this)
            % Get time length
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :returns: time length
            % :rtype: double

            out = this.time_stop - this.time_start;
        end
        
        function out = get.bandwidth_Hz(this)
            % Get bandwidth
            %
            % :param this: handle to signal object
            % :type this: :class:`report.Signal`
            %
            % :returns: bandwidth
            % :rtype: double

            out = this.freq_hi - this.freq_lo;
        end
    end
end