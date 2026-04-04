classdef Cpfsk < atomic.Signal
    properties (SetAccess = private)
        samplesPerSymbol (1,1) double {mustBePositive, mustBeInteger} = 8;
        modOrder (1,1) double {mustBePositive, mustBeInteger} = 2;
        nDataSymb (1,1) double {mustBePositive, mustBeInteger} = 100;
        modulationIndex (1,1) double {mustBePositive} = 0.5;
    end

    methods
        function this = Cpfsk(varargin)
            defaults = struct( ...
                'trafficType', "periodic", ...
                'centerFreq_Hz', nan, ...
                'transmissionRate_Hz', 250e3, ...
                'txPower_db', 0, ...
                'samplesPerSymbol', 8, ...
                'modOrder', 2, ...
                'modulationIndex', 0.5, ...
                'transmissionTotTime', 0.004, ...
                'bandwidth_Hz', nan);

            [opts, ~] = parseOptions(defaults, varargin{:});
            assert(mod(log2(opts.modOrder), 1) == 0, 'modOrder must be a power of 2');
            assert(opts.modOrder >= 2 && opts.modOrder <= 64, 'modOrder must be in [2, 64]');

            bandwidth_Hz = opts.bandwidth_Hz;
            if isnan(bandwidth_Hz)
                bandwidth_Hz = 2 * opts.transmissionRate_Hz;
            end

            this@atomic.Signal( ...
                'trafficType', opts.trafficType, ...
                'centerFreq_Hz', opts.centerFreq_Hz, ...
                'transmissionRate_Hz', opts.transmissionRate_Hz, ...
                'bandwidth_Hz', bandwidth_Hz, ...
                'txPower_db', opts.txPower_db, ...
                'protocol', report.Protocol.unknown, ...
                'modality', report.Modality.single_carrier, ...
                'modulation', report.Modulation.cpfsk);

            this.samplesPerSymbol = opts.samplesPerSymbol;
            this.modulationIndex = opts.modulationIndex;
            this.updateModOrderReport(opts.modOrder);
            this.nDataSymb = max(1, round(opts.transmissionTotTime * opts.transmissionRate_Hz));
            this.transmissionRate_Hz = this.transmissionRate_Hz * this.samplesPerSymbol;
        end

        function dataIQ = generateTransmission(this)
            x = randi([0 this.modOrder - 1], this.nDataSymb, 1);
            modObj = comm.CPFSKModulator( ...
                'ModulationOrder', this.modOrder, ...
                'ModulationIndex', this.modulationIndex, ...
                'SamplesPerSymbol', this.samplesPerSymbol);
            meanOffset = mean(0:this.modOrder - 1);
            dataIQ = modObj(2 * (x - meanOffset));
        end

        function regenerateWithRandomParams(this)
            supportedOrders = [2, 4, 8, 16];
            this.updateModOrderReport(supportedOrders(randi(numel(supportedOrders))));
            this.nDataSymb = randi([64 512]);
        end
    end

    methods (Access = private)
        function updateModOrderReport(this, modOrder)
            this.modOrder = modOrder;
            switch modOrder
                case 2
                    this.requiredMetadata.setModulation(report.Modulation.cpfsk2);
                case 4
                    this.requiredMetadata.setModulation(report.Modulation.cpfsk4);
                case 8
                    this.requiredMetadata.setModulation(report.Modulation.cpfsk8);
                case 16
                    this.requiredMetadata.setModulation(report.Modulation.cpfsk16);
                case 32
                    this.requiredMetadata.setModulation(report.Modulation.cpfsk32);
                case 64
                    this.requiredMetadata.setModulation(report.Modulation.cpfsk64);
                otherwise
                    this.requiredMetadata.setModulation(report.Modulation.cpfsk);
            end
        end
    end
end
