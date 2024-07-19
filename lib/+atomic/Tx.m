classdef Tx < handle
    % Holds transmitter properties
    
    properties (SetAccess = private)
        samplingRate_Hz (1,1) double = nan;             % Sampling rate of the transmitter
        power_db (1,1) double = 0;                      % Power of the transmitter
        location (1,3) double = [0 0 0];                % Location of the transmitter
        centerFreqRange_Hz (1,2) double = [100e6 6e9];  % Center frequency range of the transmitter
    end
    
    methods
        function this = Tx(samplingRate_Hz, power_db, location, centerFreqRange_Hz)
            % Constructor for the Tx class
            %
            % :param samplingRate_Hz: Sampling rate of the transmitter
            % :type samplingRate_Hz: double
            %
            % :param power_db: Power of the transmitter
            % :type power_db: double
            %
            % :param location: Location of the transmitter
            % :type location: (1,3) double
            %
            % :param centerFreqRange_Hz: Center frequency range of the transmitter
            % :type centerFreqRange_Hz: (1,2) double
            %
            % :return: Tx object
            % :rtype: :class:`atomic.Tx`
            
            arguments
                samplingRate_Hz (1,1) double
                power_db double = 0;
                location (1,3) double = [0, 0, 0];
                centerFreqRange_Hz (1,2) double = [100e6 6e9];
            end
            this.samplingRate_Hz = samplingRate_Hz;
            this.power_db = power_db;
            this.location = location;
            this.centerFreqRange_Hz = centerFreqRange_Hz;
        end
    end
end