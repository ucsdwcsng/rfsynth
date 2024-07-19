classdef Ds3 < atomic.Signal
    % Single bluetooth signal
    
    properties (SetAccess = private)
        chipsPerSymbol % chips per symbol (determines spreading factor)
        modOrder % modulation order
        nDataSymb = 100; % total number of data symbols to generate
        spreadType = 1; % type of dsss spread:
        % - 1 - same spread for all symbols
        % - 2 - pn sequence for each symbol
        samplesPerChip % samples per chip
        pulseShapeFlag = 0; % by default no pulse shaping
    end
    
    % constructor
    methods
        function this = Ds3(varargin)
            % Default values for optional parameters
            defaults = struct( ...
                'chipsPerSymbol', 1024, ...
                'bandwidth_Hz', nan, ...
                'modOrder', 2, ...
                'transmissionTotTime', [], ...
                'spreadType', [], ...
                'samplesPerChip', 2, ...
                'pulseShapeFlag', 0 ...
                );
            
            % Parse the optional parameters using the helper function
            [opts, unmatched] = parseOptions(defaults, varargin{:});
            
            assert(mod(log2(opts.modOrder), 1) == 0, 'modOrder must be a power of 2');

            % asser bandwidth_Hz is not nan
            assert(~isnan(opts.bandwidth_Hz), 'bandwidth_Hz must be provided');

            % compute transmissionrate hz
            transmissionRate_Hz = opts.bandwidth_Hz / (2 * opts.chipsPerSymbol);

            unmatched = [unmatched, {'protocol', report.Protocol.unknown}, {'modality',report.Modality.direct_sequence}, {'modulation',report.Modulation.unknown},...
                {'bandwidth_Hz', opts.bandwidth_Hz}, {'transmissionRate_Hz', transmissionRate_Hz}];
            this@atomic.Signal(unmatched{:});
            
            % Set the properties
            this.chipsPerSymbol = opts.chipsPerSymbol;
            this.modOrder = opts.modOrder;
            this.samplesPerChip = opts.samplesPerChip;
            this.updateModOrderReport(opts.modOrder);
            
            if ~isempty(opts.spreadType)
                this.spreadType = opts.spreadType;
            end
            
            if ~isempty(opts.transmissionTotTime)
                this.nDataSymb = round(opts.transmissionTotTime * this.transmissionRate_Hz);
            end
            
            this.transmissionRate_Hz = this.transmissionRate_Hz * this.chipsPerSymbol * this.samplesPerChip;
            this.pulseShapeFlag = opts.pulseShapeFlag;
        end
    
    
end

% public methods
methods
    
    function dataIQ = generateTransmission(this)
        % Generates the transmission
        %
        % :param this: instance of the Ds3 class
        % :type this: :class:`atomic.Ds3`
        %
        % :returns: dataIQ
        % :rtype: complex vector
        
        x = randi([0 this.modOrder - 1], this.nDataSymb, 1); % random input symbol mapped data signal
        phase_ini = pi / this.modOrder;
        y = pskmod(x, this.modOrder, phase_ini, 'gray');
        
        % spread the signal
        switch this.spreadType
            case 1
                spread_code = 2 * randi([0 1], this.chipsPerSymbol, 1) - 1;
                dataIQ = kron(y, spread_code); % multiplies each qam symbol by the spread sequence
            case 2
                spread_code = zeros(this.chipsPerSymbol, this.nDataSymb, 'like', y);
                pnSequence = comm.PNSequence('VariableSizeOutput', true, 'MaximumOutputSize', [this.chipsPerSymbol, 1]);
                
                for i = 1:this.nDataSymb
                    spread_code(:, i) = 2 * pnSequence(this.chipsPerSymbol) - 1;
                end
                
                dataIQ = y.' .* spread_code;
                dataIQ = dataIQ(:);
            otherwise
                error('unknown spread type given')
        end
        
        if numel(dataIQ) > 1e7
            dataIQ = kron(dataIQ, ones(1, this.samplesPerChip));
            dataIQ = dataIQ(:);
            
        else
            dataIQ = repmat(dataIQ, 1, this.samplesPerChip)';
            dataIQ = dataIQ(:);
        end
        
        if (this.pulseShapeFlag == 1)
            rrc = rcosdesign(0.4, 10, this.chipsPerSymbol);
            rrc = rrc.' / max(rrc);
            dataIQ = conv(dataIQ, rrc, 'same');
        end
        
    end
    
    function updateModOrderReport(this, modOrder)
        % Updates the modulation order into the required reporting field
        %
        % :param this: instance of the Ds3 class
        % :type this: :class:`atomic.Ds3`
        %
        % :param modOrder: modulation order
        % :type modOrder: int
        %
        % :returns: none
        
        this.modOrder = modOrder;
        
        switch this.modOrder
            case 2
                this.requiredMetadata.setModulation(report.Modulation.bpsk)
            case 4
                this.requiredMetadata.setModulation(report.Modulation.qpsk)
            case 8
                this.requiredMetadata.setModulation(report.Modulation.qam)
            case {16, 32, 64, 128, 256}
                this.requiredMetadata.setModulation(report.Modulation.qam)
                
            otherwise
                error("Illegal modOrder for QAM")
        end
        
    end
    
    function regenerateWithRandomParams(this)
        % Randomizes atomic_sig_gen_param for variety in data set generation
        %
        % :param this: instance of the Ds3 class
        % :type this: :class:`atomic.Ds3`
        %
        % :returns: none
        
        % Randomize generator params
        this.modOrder = 2 ^ randi([1 4]);
        this.nDataSymb = randi([64 512]);
        
        if this.requiredMetadata.activity_type == report.Activity.overt_anomaly
            this.centerFreq_Hz = randi([1 1e6], 1);
            this.bandwidth_Hz = randi([1 1e3]);
        end
        
    end
    
end

methods (Static)
    function [trafficType, centerFreq_Hz, transmissionRate_Hz, txPower_db, ...
            chipsPerSymbol, ...
            modOrder, ...
            transmissionTotTime, ...
            spreadType, ...
            samplesPerChip, ...
            pulseShapeFlag] = getParameters(instanceSelect, parameterSelect)
        % Returns the parameters for the given instance and parameter select
        %
        % :param instanceSelect: instance name
        % :type instanceSelect: string
        %
        % :param parameterSelect: parameter name
        % :type parameterSelect: string
        %
        % :returns: tuple containing the parameters
        % :rtype: tuple
        
        centerFreq_Hz = [2.450e9];
        
        txPower_db = [-10:1:0];
        chipsPerSymbol = [7, 15, 31, 63];
        modOrder = [4, 8, 16];
        transmissionTotTime = [4 8 16] * 1e-3;
        spreadType = 1;
        samplesPerChip = [2, 4, 6, 8, 10];
        pulseShapeFlag = true;
        
        transmissionRate_Hz = 20e6 / (31 * 6);
        
        trafficType = ["periodic", "poisson"];
        transmissionPerSec = 10:1:25;
        
        switch instanceSelect
            case 'default'
            case 'custom0'
                transmissionRate_Hz = 10e6 ./ (chipsPerSymbol * samplesPerChip);
            otherwise
                error('Ds3:NotImplemented', "%s instanceSelect not implemented\n", instanceSelect);
        end
        
        %
        [trafficType, transmissionPerSec, centerFreq_Hz, transmissionRate_Hz, txPower_db, ...
            chipsPerSymbol, ...
            modOrder, ...
            transmissionTotTime, ...
            spreadType, ...
            samplesPerChip, ...
            pulseShapeFlag] = atomic.Signal.executeParameterSelect(parameterSelect, trafficType, transmissionPerSec, centerFreq_Hz, transmissionRate_Hz, txPower_db, ...
            chipsPerSymbol, ...
            modOrder, ...
            transmissionTotTime, ...
            spreadType, ...
            samplesPerChip, ...
            pulseShapeFlag);
        
        trafficType = atomic.Traffic(trafficType(1), "transmissionPerSec", transmissionPerSec(1));
    end
    
end

end
