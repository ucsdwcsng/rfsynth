classdef Fsk < atomic.Signal
    properties (SetAccess = private)
        samplesPerSymbol (1,1) double {mustBePositive, mustBeInteger} = 8;
        modOrder (1,1) double {mustBePositive, mustBeInteger} = 2;
        nDataSymb (1,1) double {mustBePositive, mustBeInteger} = 100;
        freqDev (1,1) double {mustBePositive} = 0.25;
    end

    methods
        function this = Fsk(varargin)
            defaults = struct( ...
                'trafficType', "periodic", ...
                'centerFreq_Hz', nan, ...
                'transmissionRate_Hz', 250e3, ...
                'txPower_db', 0, ...
                'samplesPerSymbol', 8, ...
                'modOrder', 2, ...
                'freqDev', 0.25, ...
                'transmissionTotTime', 0.004, ...
                'bandwidth_Hz', nan);

            [opts, ~] = parseOptions(defaults, varargin{:});
            assert(mod(log2(opts.modOrder), 1) == 0, 'modOrder must be a power of 2');
            assert(opts.modOrder >= 2 && opts.modOrder <= 128, 'modOrder must be in [2, 128]');

            bandwidth_Hz = opts.bandwidth_Hz;
            if isnan(bandwidth_Hz)
                bandwidth_Hz = opts.transmissionRate_Hz * (1 + 2 * opts.freqDev * (opts.modOrder - 1));
            end

            this@atomic.Signal( ...
                'trafficType', opts.trafficType, ...
                'centerFreq_Hz', opts.centerFreq_Hz, ...
                'transmissionRate_Hz', opts.transmissionRate_Hz, ...
                'bandwidth_Hz', bandwidth_Hz, ...
                'txPower_db', opts.txPower_db, ...
                'protocol', report.Protocol.unknown, ...
                'modality', report.Modality.single_carrier, ...
                'modulation', report.Modulation.fsk2);

            this.samplesPerSymbol = opts.samplesPerSymbol;
            this.freqDev = opts.freqDev;
            this.updateModOrderReport(opts.modOrder);
            this.nDataSymb = max(1, round(opts.transmissionTotTime * opts.transmissionRate_Hz));
            this.transmissionRate_Hz = this.transmissionRate_Hz * this.samplesPerSymbol;
        end

        function dataIQ = generateTransmission(this)
            sampleFreq_Hz = this.transmissionRate_Hz;
            x = randi([0 this.modOrder - 1], this.nDataSymb, 1);
            freq_sep = this.freqDev * sampleFreq_Hz / max(this.modOrder - 1, 1);
            dataIQ = fskmod(x, this.modOrder, freq_sep, this.samplesPerSymbol, sampleFreq_Hz, 'discont');
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
                    this.requiredMetadata.setModulation(report.Modulation.fsk2);
                case 4
                    this.requiredMetadata.setModulation(report.Modulation.fsk4);
                case 8
                    this.requiredMetadata.setModulation(report.Modulation.fsk8);
                case 16
                    this.requiredMetadata.setModulation(report.Modulation.fsk16);
                case 32
                    this.requiredMetadata.setModulation(report.Modulation.fsk32);
                case 64
                    this.requiredMetadata.setModulation(report.Modulation.fsk64);
                case 128
                    this.requiredMetadata.setModulation(report.Modulation.fsk128);
                otherwise
                    error('Illegal modOrder for FSK');
            end
        end
    end
end
