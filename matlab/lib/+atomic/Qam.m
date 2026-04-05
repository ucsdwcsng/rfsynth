classdef Qam < atomic.Signal
    properties (SetAccess = private)
        samplesPerSymbol (1,1) double {mustBePositive, mustBeInteger} = 8;
        modOrder (1,1) double {mustBePositive, mustBeInteger} = 4;
        symbolRate (1,1) double = 1e6;
        nDataSymb (1,1) double {mustBePositive, mustBeInteger} = 100;
        beta (1,1) double {mustBeNonnegative} = 0.35;
        span (1,1) double {mustBePositive, mustBeInteger} = 10;
        testVectorPath string = "";
    end

    methods
        function this = Qam(varargin)
            defaults = struct( ...
                'trafficType', "periodic", ...
                'centerFreq_Hz', nan, ...
                'transmissionRate_Hz', 1e6, ...
                'txPower_db', 0, ...
                'samplesPerSymbol', 8, ...
                'modOrder', 4, ...
                'beta', 0.35, ...
                'span', 10, ...
                'transmissionTotTime', 0.004, ...
                'testVectorPath', "");

            [opts, ~] = parseOptions(defaults, varargin{:});
            bandwidth_Hz = opts.transmissionRate_Hz * (1 + opts.beta);

            this@atomic.Signal( ...
                'trafficType', opts.trafficType, ...
                'centerFreq_Hz', opts.centerFreq_Hz, ...
                'transmissionRate_Hz', opts.transmissionRate_Hz, ...
                'bandwidth_Hz', bandwidth_Hz, ...
                'txPower_db', opts.txPower_db, ...
                'protocol', report.Protocol.unknown, ...
                'modality', report.Modality.single_carrier, ...
                'modulation', report.Modulation.qam);

            this.symbolRate = opts.transmissionRate_Hz;
            this.samplesPerSymbol = opts.samplesPerSymbol;
            this.beta = opts.beta;
            this.span = opts.span;
            this.testVectorPath = string(opts.testVectorPath);
            this.updateModOrderReport(opts.modOrder);
            this.nDataSymb = max(1, round(opts.transmissionTotTime * this.symbolRate));
            this.transmissionRate_Hz = this.transmissionRate_Hz * this.samplesPerSymbol;
        end

        function dataIQ = generateTransmission(this)
            if strlength(this.testVectorPath) > 0
                vec = load_atomic_test_vector(this.testVectorPath);
                y1 = vec.payload.symbols(:);
            else
                x = randi([0 this.modOrder - 1], this.nDataSymb, 1);
                y1 = qammod(x, this.modOrder, 'gray');
            end
            y2 = upsample(y1, this.samplesPerSymbol);
            rrc = rcosdesign(this.beta, this.span, this.samplesPerSymbol);
            rrc = rrc.' / rms(rrc);
            dataIQ = conv(y2, rrc, 'same');
        end

        function regenerateWithRandomParams(this)
            supportedOrders = [2, 4, 8, 16, 32, 64, 128, 256];
            this.updateModOrderReport(supportedOrders(randi(numel(supportedOrders))));
            this.nDataSymb = randi([64 512]);
        end
    end

    methods (Access = private)
        function updateModOrderReport(this, modOrder)
            this.modOrder = modOrder;
            switch modOrder
                case 2
                    this.requiredMetadata.setModulation(report.Modulation.bpsk);
                case 4
                    this.requiredMetadata.setModulation(report.Modulation.qpsk);
                case 8
                    this.requiredMetadata.setModulation(report.Modulation.qam8);
                case 16
                    this.requiredMetadata.setModulation(report.Modulation.qam16);
                case 32
                    this.requiredMetadata.setModulation(report.Modulation.qam32);
                case 64
                    this.requiredMetadata.setModulation(report.Modulation.qam64);
                case 128
                    this.requiredMetadata.setModulation(report.Modulation.qam128);
                case 256
                    this.requiredMetadata.setModulation(report.Modulation.qam256);
                case 1024
                    this.requiredMetadata.setModulation(report.Modulation.qam1024);
                otherwise
                    this.requiredMetadata.setModulation(report.Modulation.qam);
            end
        end
    end
end
