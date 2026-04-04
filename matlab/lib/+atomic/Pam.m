classdef Pam < atomic.Signal
    properties (SetAccess = private)
        samplesPerSymbol (1,1) double {mustBePositive, mustBeInteger} = 8;
        modOrder (1,1) double {mustBePositive, mustBeInteger} = 4;
        nDataSymb (1,1) double {mustBePositive, mustBeInteger} = 100;
        beta (1,1) double {mustBeNonnegative} = 0.35;
        span (1,1) double {mustBePositive, mustBeInteger} = 10;
    end

    methods
        function this = Pam(varargin)
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
                'bandwidth_Hz', nan);

            [opts, ~] = parseOptions(defaults, varargin{:});
            bandwidth_Hz = opts.bandwidth_Hz;
            if isnan(bandwidth_Hz)
                bandwidth_Hz = opts.transmissionRate_Hz * (1 + opts.beta);
            end

            this@atomic.Signal( ...
                'trafficType', opts.trafficType, ...
                'centerFreq_Hz', opts.centerFreq_Hz, ...
                'transmissionRate_Hz', opts.transmissionRate_Hz, ...
                'bandwidth_Hz', bandwidth_Hz, ...
                'txPower_db', opts.txPower_db, ...
                'protocol', report.Protocol.unknown, ...
                'modality', report.Modality.single_carrier, ...
                'modulation', report.Modulation.pam);

            this.samplesPerSymbol = opts.samplesPerSymbol;
            this.modOrder = opts.modOrder;
            this.beta = opts.beta;
            this.span = opts.span;
            this.nDataSymb = max(1, round(opts.transmissionTotTime * opts.transmissionRate_Hz));
            this.transmissionRate_Hz = this.transmissionRate_Hz * this.samplesPerSymbol;
        end

        function dataIQ = generateTransmission(this)
            x = randi([0 this.modOrder - 1], this.nDataSymb, 1);
            y = pammod(x, this.modOrder, 0, 'gray');
            y = upsample(y, this.samplesPerSymbol);
            rrc = rcosdesign(this.beta, this.span, this.samplesPerSymbol);
            rrc = rrc.' / rms(rrc);
            dataIQ = conv(y, rrc, 'same');
            dataIQ = complex(dataIQ, 0);
        end

        function regenerateWithRandomParams(this)
            supportedOrders = [2, 4, 8, 16];
            this.modOrder = supportedOrders(randi(numel(supportedOrders)));
            this.nDataSymb = randi([64 512]);
        end
    end
end
