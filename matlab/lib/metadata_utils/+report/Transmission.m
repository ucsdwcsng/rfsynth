classdef Transmission < handle
    % Represents a single transmission 

    % constant for metadata type id
    properties (Constant)
        report_type = "energy";                             % type of report
    end

    % required inputs
    properties (SetAccess = private)
        % unique identifier
        instance_name string                                % unique instance identifier

        % required properties to even consider report
        time_start (1,1) double                             % transmission start time [s]
        time_stop (1,1) double                              % transmission stop time [s]
        freq_lo (1,1) double                                % low frequency bound [Hz]
        freq_hi (1,1) double                                % high frequency bound [Hz]
    end
    
    properties (Dependent)
        % others
        timeLength_s (1,1) double                           % time length [s]          
        bandwidth_Hz (1,1) double                           % bandwidth [Hz]
    end
    
    methods

        function this = Transmission(time_start, time_stop, freq_lo, freq_hi, instance_name)
            % Constructor for Transmission 
            %
            % :param time_start: transmission start time [s]
            % :type time_start: double
            %
            % :param time_stop: transmission stop time [s]
            % :type time_stop: double
            %
            % :param freq_lo: low frequency bound [Hz]
            % :type freq_lo: double
            %
            % :param freq_hi: high frequency bound [Hz]
            % :type freq_hi: double
            %
            % :param instance_name: unique instance identifier
            % :type instance_name: string
            %
            % :returns: handle to Transmission object
            % :rtype: :class:`report.Transmission`

            arguments
                time_start = 0
                time_stop = 0
                freq_lo = 0
                freq_hi = 0
                instance_name = "DEADBEEFDEADBEEF"
            end
            this.time_start = time_start;
            this.time_stop = time_stop;
            this.freq_lo = freq_lo;
            this.freq_hi = freq_hi;
            this.instance_name = instance_name;
        end
    end
    
    % getters
    methods
        function out = get.timeLength_s(this)
            % Get time length of transmission
            %
            % :param this: handle to Transmission object
            % :type this: :class:`report.Transmission`
            %
            % :returns: time length [s]
            % :rtype: double

            out = this.time_stop - this.time_start;
        end
        
        function out = get.bandwidth_Hz(this)
            % Get bandwidth of transmission
            %
            % :param this: handle to Transmission object
            % :type this: :class:`report.Transmission`
            %
            % :returns: bandwidth [Hz]
            % :rtype: double
            
            out = this.freq_hi - this.freq_lo;
        end
    end
end