classdef Ofdm < atomic.Signal
    properties (SetAccess = private)
        Nfft (1,1) double {mustBeMember(Nfft,[64, 128, 256, 512, 1024, 2048])} = 64;
        ofdm_params struct
    end

    methods
        function json = jsonencode(this, varargin)
            sAll = struct(this);
            structFieldnames = fieldnames(sAll.ofdm_params);
            for i = 1:numel(structFieldnames)
                fieldValue = sAll.ofdm_params.(structFieldnames{i});
                if ~isreal(fieldValue)
                    sAll.ofdm_params.(structFieldnames{i}) = struct( ...
                        'real', real(fieldValue), ...
                        'imag', imag(fieldValue));
                end
            end
            json = jsonencode(sAll, varargin{:});
        end
    end

    methods
        function this = Ofdm(varargin)
            defaults = struct( ...
                'trafficType', atomic.Traffic("periodic", "transmissionPerSec", 100), ...
                'centerFreq_Hz', nan, ...
                'transmissionRate_Hz', 10e6, ...
                'txPower_db', 0, ...
                'Nfft', 256, ...
                'modOrder', 4, ...
                'transmissionTotTime', 0.004);

            [opts, ~] = parseOptions(defaults, varargin{:});
            ofdm_params = wcsng_ofdm_param_gen('N_SC', opts.Nfft);
            ofdm_params.N_OFDM_SYMS = max(1, floor((opts.transmissionTotTime * opts.transmissionRate_Hz) / (opts.Nfft + ofdm_params.CP_LEN)));
            ofdm_params.N_STS = 0;
            ofdm_params.MOD_ORDER = opts.modOrder;
            bandwidth_Hz = (numel(ofdm_params.FILLED_SC_IND) + 1) / opts.Nfft * opts.transmissionRate_Hz;

            this@atomic.Signal( ...
                'trafficType', opts.trafficType, ...
                'centerFreq_Hz', opts.centerFreq_Hz, ...
                'transmissionRate_Hz', opts.transmissionRate_Hz, ...
                'bandwidth_Hz', bandwidth_Hz, ...
                'txPower_db', opts.txPower_db, ...
                'protocol', report.Protocol.unknown, ...
                'modality', report.Modality.multi_carrier, ...
                'modulation', report.Modulation.ofdm);

            this.Nfft = opts.Nfft;
            this.ofdm_params = ofdm_params;
        end

        function dataIQ = generateTransmission(this)
            [dataIQ, ~] = ofdm_tx(this.ofdm_params);
        end

        function regenerateWithRandomParams(this)
            supportedOrders = [2, 4, 16, 64];
            this.ofdm_params.MOD_ORDER = supportedOrders(randi(numel(supportedOrders)));
            this.ofdm_params.N_OFDM_SYMS = randi([10 200]);
        end
    end
end
