classdef RFImperfections
    % A self documenting class that holds the values and
    % ranges of RF imperfections like DC Offset, CFO, IQ Imbalance etc.
    
    properties (SetAccess = private)
        freqOffset (1,1) double = 0;                % Frequency offset [Hz]
        freqOffsetRange (1,2) double = [0,0];       % Frequency offset range [Hz]
        imbalIQ (2,1) double = [0;0];               % IQ imbalance [gain_unbal, phase_unbal]. [linear, radian]
        imbalIQRange (2,2) double = zeros(2,2);     % IQ imbalance range [gain_unbal, phase_unbal]. [linear, radian]
        offsetDC (2,1) double = [0;0];              % DC offset [relativeGain, phase]. [linear, radian]
        offsetDCRange (2,2) double = zeros(2,2);    % DC offset range [relativeGain, phase]. [linear, radian]
    end
    
    
    methods
        function this = RFImperfections(freqOffset,imbalIQ,offsetDC,NameValueArgs)
            % Construct an instance of this class
            %
            % :param freqOffset: Frequency offset [Hz]
            % :type freqOffset: double
            %
            % :param imbalIQ: IQ imbalance [gain_unbal, phase_unbal]. [linear, radian]
            % :type imbalIQ: (2x1) array[double]
            %
            % :param offsetDC: DC offset [relativeGain, phase]. [linear, radian]
            % :type offsetDC: (2x1) array[double]
            %
            % :param NameValueArgs.imbalIQRange: IQ imbalance range [gain_unbal, phase_unbal]. [linear, radian]
            % :type NameValueArgs.imbalIQRange: (2x2) array[double]
            %
            % :param NameValueArgs.freqOffsetRange: Frequency offset range [Hz]
            % :type NameValueArgs.freqOffsetRange: (1,2) array[double]
            %
            % :param NameValueArgs.offsetDCRange: DC offset range [relativeGain, phase]. [linear, radian]
            % :type NameValueArgs.offsetDCRange: (2,2) array[double]
            %
            % :return: instance of the RFImperfections class
            % :rtype: :class:`atomic.RFImperfections`
            
            
            arguments
                freqOffset (1,1) double = 0;
                imbalIQ (2,1) double = [0;0];
                offsetDC (2,1) double = [0;0];
                NameValueArgs.imbalIQRange (2,2) double
                NameValueArgs.freqOffsetRange (1,2) double
                NameValueArgs.offsetDCRange (2,2) double
            end
            
            this.freqOffset = freqOffset;
            this.imbalIQ = imbalIQ;
            this.offsetDC = offsetDC;
            
            if(isfield(NameValueArgs,'freqOffsetRange'))
                this.freqOffsetRange = NameValueArgs.freqOffsetRange;
            else
                this.freqOffsetRange = [freqOffset,freqOffset];
            end
            
            if(isfield(NameValueArgs,'imbalIQRange'))
                this.imbalIQRange = NameValueArgs.imbalIQRange;
            else
                this.imbalIQRange = [imbalIQ,imbalIQ];
            end
            if(isfield(NameValueArgs,'offsetDCRange'))
                this.offsetDCRange = NameValueArgs.offsetDCRange;
            else
                this.offsetDCRange = [offsetDC,offsetDC];
            end
        end
        
        %Setter for range
        function this = setRanges(this,NameValueArgs)
            % Construct an instance of this class
            %
            % :param this: instance of the RFImperfections class
            % :type this: :class:`atomic.RFImperfections`
            %
            % :param NameValueArgs: Name value pairs
            % :type NameValueArgs: :class:`matlab.lang.NameValueArgs`
            %
            % :return: instance of the RFImperfections class with updated ranges
            % :rtype: :class:`atomic.RFImperfections`
            
            
            arguments
                this
                NameValueArgs.imbalIQRange (2,2) double
                NameValueArgs.freqOffsetRange (1,2) double
                NameValueArgs.offsetDCRange (2,2) double
            end
            
            if(isfield(NameValueArgs,'freqOffsetRange'))
                this.freqOffsetRange = NameValueArgs.freqOffsetRange;
            end
            if(isfield(NameValueArgs,'imbalIQRange'))
                this.imbalIQRange = NameValueArgs.imbalIQRange;
            end
            if(isfield(NameValueArgs,'offsetDCRange'))
                this.offsetDCRange = NameValueArgs.offsetDCRange;
            end
        end
        
        function this = regenerateWithRandomParams(this)
            % Randomizes the imperfections within the given limits
            %
            % :param this: instance of the RFImperfections class
            % :type this: :class:`atomic.RFImperfections`
            %
            % :return: instance of the RFImperfections class with updated imperfections
            % :rtype: :class:`atomic.RFImperfections`
            
            
            if(diff(this.freqOffsetRange))
                this.freqOffset = this.freqOffsetRange(1) + rand*diff(this.freqOffsetRange);
            end
            
            if(diff(this.imbalIQRange(1,:)))
                this.imbalIQ(1) = this.imbalIQ(1) + rand*diff(this.imbalIQRange(1,:));
            end
            if(diff(this.imbalIQRange(2,:)))
                this.imbalIQ(2) = this.imbalIQ(2) + rand*diff(this.imbalIQRange(2,:));
            end
            
            if(diff(this.offsetDCRange(1,:)))
                this.offsetDCRange(1) = this.offsetDCRange(1) + rand*diff(this.offsetDCRange(1,:));
            end
            if(diff(this.offsetDCRange(2,:)))
                this.offsetDCRange(2) = this.offsetDCRange(2) + rand*diff(this.offsetDCRange(2,:));
            end
        end
        
        
    end
end
