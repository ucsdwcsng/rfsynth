classdef Traffic < handle
    % Holds a traffic type and other additional information as required.
    
    properties (SetAccess = protected)
        trafficType string                              % Type of traffic
        startTime double = 0;                           % Start time of the traffic
        stopTime double = Inf;                          % Stop time of the traffic
        transmissionPerSec                              % Number of transmissions per second
        arrivalArray                                    % Array of arrival times
        varRange                                        % Variance range for the arrival time (in seconds)
        energies_per_burst double = double.empty();     % Number of energies per burst
        time_per_energy double = double.empty();        % Time per energy
        burst_select double = false;                    % Burst mode toggle
        time_bet_energy double = 1e-3;                  % Time between energies
        timeOn double = double.empty();                 % Time on
    end
    
    properties
        
    end
    
    methods
        function this = Traffic(trafficType,NameValueArgs)
            % Constructor for the Traffic class
            %
            % :param trafficType: Type of traffic
            % :type trafficType: str
            %
            % :param NameValueArgs: Name value pairs
            % :type NameValueArgs: :class:`matlab.lang.NameValueArgs`
            %
            % :returns: Traffic object
            % :rtype: :class:`atomic.Traffic`
            
            
            arguments
                trafficType string = "periodic"
                NameValueArgs.startTime double = 0; % Begins immediately
                NameValueArgs.stopTime double = Inf; % Lasts forever
                NameValueArgs.arrivalArray (:,1) double = double.empty(0,1);
                NameValueArgs.varRange double = double.empty();
                NameValueArgs.transmissionPerSec double = double.empty();
                NameValueArgs.burst_tog logical = false;
                NameValueArgs.energies_per_burst double = double.empty();
                NameValueArgs.time_per_energy double = double.empty();
                NameValueArgs.timeOn double = double.empty();
            end
            this.trafficType = string(trafficType);
            this.startTime = NameValueArgs.startTime;
            this.stopTime = NameValueArgs.stopTime;
            this.arrivalArray = NameValueArgs.arrivalArray;
            this.varRange = NameValueArgs.varRange;
            this.timeOn = NameValueArgs.timeOn;
            
            if isempty(this.timeOn)
                this.timeOn = this.stopTime - this.startTime;
            end
            
            if ~isempty(this.arrivalArray)
                this.startTime = min(this.arrivalArray);
                this.stopTime = max(this.arrivalArray) + this.timeOn;
            end
            
            if NameValueArgs.burst_tog
                this.burst_select = NameValueArgs.burst_tog;
                this.energies_per_burst = NameValueArgs.energies_per_burst;
                this.time_per_energy= NameValueArgs.time_per_energy;
                this.time_bet_energy = 1e-3;
            end
            this.setTransmissionPerSec(NameValueArgs.transmissionPerSec);
        end
        
        function transmissionStartTimes = getTransmissionTimes(this, timeStop, timeStart)
            % Returns transmission start times according to class properties and input parameters
            %
            % :param this: Traffic object
            % :type this: :class:`atomic.Traffic`
            %
            % :param timeStop: Stop time of the simulation
            % :type timeStop: double
            %
            % :param timeStart: Start time of the simulation
            % :type timeStart: double
            %
            % :returns: Transmission start times
            % :rtype: array[double]
            
            
            arguments
                this
                timeStop double
                timeStart double = 0; % Start immediately
            end
            assert(~isempty(this.transmissionPerSec) || strcmp(this.trafficType, "customArray"),'Transmissions per second is not set!');
            
            % Check if there is overlap
            request_interval = fixed.Interval(timeStart, timeStop);
            signal_interval = fixed.Interval(this.startTime, this.stopTime);
            
            intersect_interval = intersect(signal_interval, request_interval);
            
            if isempty(intersect_interval)
                transmissionStartTimes = [];
                return
            end
            
            % Generate start_times from start of signal to the end of
            % requested time.
            % We will then slice the vector
            switch this.trafficType
                case "poisson"
                    % Interarrival times are exponential -> Poisson point process
                    nTransmissionAvg = floor((timeStop - this.startTime) * this.transmissionPerSec);
                    transmissionStartTimes = exprnd(1/this.transmissionPerSec, nTransmissionAvg*4, 1);
                    transmissionStartTimes = cumsum(transmissionStartTimes);
                    
                    transmissionStartTimes = transmissionStartTimes + this.startTime;
                    
                    transmissionStartTimes = transmissionStartTimes(transmissionStartTimes < timeStop);
                    %burst mode code
                    if this.burst_select
                        start_arr = repelem(transmissionStartTimes,this.energies_per_burst);
                        factor = 1:this.energies_per_burst;
                        offset = repelem(this.time_per_energy,this.energies_per_burst);
                        energy_off = repelem(this.time_bet_energy,this.energies_per_burst);
                        offset = offset + energy_off;
                        energy_t_offset = factor .*offset;
                        time_offset = repmat(energy_t_offset,1,length(start_arr)/this.energies_per_burst);
                        transmissionStartTimes = start_arr + time_offset;
                    end
                    transmissionStartTimes = transmissionStartTimes.';
                    
                case "periodic"
                    % Interarrival times are fixed
                    nTransmission = ceil((timeStop - this.startTime) * this.transmissionPerSec);
                    transmissionStartTimes = (0 : nTransmission-1) / this.transmissionPerSec;
                    %burst mode code
                    if this.burst_select
                        start_arr = repelem(transmissionStartTimes,this.energies_per_burst);
                        factor = 1:this.energies_per_burst;
                        offset = repelem(this.time_per_energy,this.energies_per_burst);
                        energy_off = repelem(this.time_bet_energy,this.energies_per_burst);
                        offset = offset + energy_off;
                        energy_t_offset = factor .*offset;
                        time_offset = repmat(energy_t_offset,1,length(start_arr)/this.energies_per_burst);
                        transmissionStartTimes = start_arr + time_offset;
                    end
                    transmissionStartTimes = transmissionStartTimes.';
                    transmissionStartTimes = transmissionStartTimes + this.startTime;
                    
                    
                    
                case "uniformVar"
                    % Interarrival times are uniformly distributed in a range around
                    % the mean
                    nTransmissionAvg = ceil((timeStop - this.startTime) * this.transmissionPerSec);
                    transmissionStartTimeMean = (1./this.transmissionPerSec);
                    
                    if(isempty(this.varRange))
                        startTimeVar = 0.075*transmissionStartTimeMean;
                    else
                        startTimeVar =  this.varRange;
                    end
                    
                    transmissionStartTimes = (1./this.transmissionPerSec) + unifrnd(-startTimeVar...
                        , startTimeVar,[1, nTransmissionAvg*2]);
                    transmissionStartTimes = cumsum(transmissionStartTimes);
                    transmissionStartTimes = transmissionStartTimes + this.startTime;
                    
                    transmissionStartTimes = transmissionStartTimes(transmissionStartTimes < timeStop);
                    %burst mode code
                    if this.burst_select
                        start_arr = repelem(transmissionStartTimes,this.energies_per_burst);
                        factor = 1:this.energies_per_burst;
                        offset = repelem(this.time_per_energy,this.energies_per_burst);
                        energy_off = repelem(this.time_bet_energy,this.energies_per_burst);
                        offset = offset + energy_off;
                        energy_t_offset = factor .*offset;
                        time_offset = repmat(energy_t_offset,1,length(start_arr)/this.energies_per_burst);
                        transmissionStartTimes = start_arr + time_offset;
                    end
                    
                    transmissionStartTimes = transmissionStartTimes.';
                    
                    
                    
                case "fullBurst"
                    % All signals are sent back-to-back in slots
                    
                    burst_ivl = ((timeStop-this.startTime) - this.time_per_burst*this.num_bursts)/(this.num_bursts);
                    energy_ivl = (this.time_per_burst - this.energies_per_burst * this.time_per_energy)/(this.energies_per_burst);
                    assert( energy_ivl >0,"Wrong parameters");
                    start = this.startTime;
                    transmissionStartTimes=[];
                    
                    for idx = 1:this.num_bursts
                        start_arr = start:this.time_per_energy+energy_ivl:start+this.time_per_burst;
                        start = start+this.time_per_burst+burst_ivl;
                        transmissionStartTimes = [transmissionStartTimes start_arr];
                        
                    end
                case "customArray"
                    % TODO: jank fix to enable arbitrary time placement
                    transmissionStartTimes = this.arrivalArray;
                    
                otherwise
                    
                    error("Unknown traffic_type")
            end
            
            % Slice start times so that they are within range
            transmissionStartTimes = transmissionStartTimes(transmissionStartTimes >= intersect_interval.LeftEnd);
            transmissionStartTimes = transmissionStartTimes(transmissionStartTimes <= intersect_interval.RightEnd);
            
            
        end
        
        % Setter
        function this = setTransmissionPerSec(this, transmissionPerSec)
            % Set the number of transmissions per second
            %
            % :param this: Traffic object
            % :type this: :class:`atomic.Traffic`
            %
            % :param transmissionPerSec: Number of transmissions per second
            % :type transmissionPerSec: double
            %
            % :return: None
            
            this.transmissionPerSec = transmissionPerSec;
        end
    end
end

