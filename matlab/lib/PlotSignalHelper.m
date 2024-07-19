classdef PlotSignalHelper < handle
    % Signal Plotting Helper Class 
    %

    
    properties
        % General Parameters
        isUseTimeScale (1,1) logical        = false;    % Sample indices instead of time
        isApplyFftShift (1,1) logical       = true;     % Control FFT-shift behaviour
        isHoldAllSubplots (1,1) logical     = false;    % Hold all the subplots?
        isAlsoShowImag (1,1) logical        = true;     % Show both Real and Imag?
        
        % Signal Parameters
        sampleFreq_Hz (1,1) double          = 25e6;     % Sampling Frequency
        
        % Processing Parameters
        oversampleFactor (1,1) double       = 1;        % Oversampling Factor
        oversampleFreqFactor (1,1) double   = 1;        % Freq Domain Oversampling Factor
        
        % STFT Parameters
        nFFT (1,1) double                   = 1024;     % FFT Size
        nOverlap (1,1) double               = 128;      % Overlap Size  
        nWindow (1,1) double                = 256;      % Window Size
        isPlotStft (1,1) double             = 1;        % Plot STFT?
    end
    
%     methods
%         end
%     end
%     
    methods
        function plotSignal(this, signalIQ, engineObj, figHandle)
            % Plot Signal
            %
            % :param this: handle to PlotSignalHelper
            % :type this: :class:`PlotSignalHelper`
            %
            % :param signalIQ: Signal to plot
            % :type signalIQ: vector[complex double]
            %
            % :param engineObj: Engine Object
            % :type engineObj: :class:`Engine`
            %
            % :param figHandle: Figure handle
            % :type figHandle: handle
            %
            % :returns: None

            if nargin < 3 
                engineObj = [];
            end
            if nargin < 4 || isempty(figHandle)
                figure();
            else
                figure(figHandle)
            end
            
            if this.isUseTimeScale
                spectrogram(signalIQ, ...
                    this.nWindow, ...
                    this.nOverlap, ...
                    this.nFFT, ...
                    this.sampleFreq_Hz, ...
                    'centered');
            else
                spectrogram(signalIQ, ...
                    this.nWindow, ...
                    this.nOverlap, ...
                    this.nFFT, ...
                    'centered');
            end
            
            % draw tf box around signal
            if ~isempty(engineObj)
                for i = 1:numel(engineObj.sourceArray)
                    iSource = engineObj.sourceArray(i);
                    for j = 1:numel(iSource.signalArray)
                        iSignal = iSource.signalArray(j);
                        for m = 1:numel(iSignal.transmissionArray)
                            iTx = iSignal.transmissionArray(m);
                            rectBoxPos = [iTx.freq_lo-engineObj.rxObj.freqCenter_Hz, iTx.time_start, iTx.bandwidth_Hz, iTx.timeLength_s];
                            rectBoxPos([1 3]) = rectBoxPos([1 3]) / 1e6; % units of MHz
                            rectBoxPos([2 4]) = rectBoxPos([2 4]) / 1e-3; % units of ms
                            rectangle('Position', rectBoxPos, ...
                                'LineWidth', 2, ...
                                'EdgeColor', 'r');
                        end
                    end
                end
            end
        end
    end
    
end