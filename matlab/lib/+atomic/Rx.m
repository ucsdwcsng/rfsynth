classdef Rx < handle
    % Holds receiver properties
    
    properties (Constant)
        report_type = "receiver";       % type of report
    end
    
    properties (SetAccess = private)
        instance_name (1,1) string      % Name of the instance
        sampleRate_Hz (1,1) double      % Sample rate [Hz]
        freqCenter_Hz (1,1) double      % Center frequency [Hz]
        location (1,3) double           % Location of the receiver in meters
        noiseProfile                    % Noise profile
        isOn (1,1) logical              % Whether receiver is on or off
    end
    
    methods
        function this = Rx(instance_name, sampleRate_Hz, freqCenter_Hz, location)
            % Constructor for Rx class
            %
            % :param instance_name: Name of the instance
            % :type instance_name: str
            %
            % :param sampleRate_Hz: Sample rate in Hz
            % :type sampleRate_Hz: double
            %
            % :param freqCenter_Hz: Center frequency in Hz
            % :type freqCenter_Hz: double
            %
            % :param location: Location of the receiver in meters
            % :type location: (1x3) array[double]
            %
            % :returns: Rx object
            % :rtype: Rx
            
            
            this.instance_name = instance_name;
            this.sampleRate_Hz = sampleRate_Hz;
            this.freqCenter_Hz = freqCenter_Hz;
            this.location = location;
        end
    end
end