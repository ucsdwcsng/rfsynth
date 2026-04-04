classdef FreqHopping < atomic.Signal
    properties (SetAccess = private)
        nHops (1,1) double {mustBePositive, mustBeInteger} = 5;
        bandwidthPerHop_Hz (1,1) double {mustBePositive} = 500e3;
        guardTime_s (1,1) double {mustBeNonnegative} = 50e-6;
        transmissionTotTime (1,1) double {mustBePositive} = 0.004;
    end

    methods
        function this = FreqHopping(varargin)
            defaults = struct( ...
                'trafficType', "periodic", ...
                'centerFreq_Hz', nan, ...
                'transmissionRate_Hz', 10e6, ...
                'bandwidth_Hz', 10e6, ...
                'txPower_db', 0, ...
                'nHops', 5, ...
                'bandwidthPerHop_Hz', 500e3, ...
                'guardTime_s', 50e-6, ...
                'transmissionTotTime', 0.004);

            [opts, ~] = parseOptions(defaults, varargin{:});

            this@atomic.Signal( ...
                'trafficType', opts.trafficType, ...
                'centerFreq_Hz', opts.centerFreq_Hz, ...
                'transmissionRate_Hz', opts.transmissionRate_Hz, ...
                'bandwidth_Hz', opts.bandwidth_Hz, ...
                'txPower_db', opts.txPower_db, ...
                'protocol', report.Protocol.unknown, ...
                'modality', report.Modality.frequency_agile, ...
                'modulation', report.Modulation.fh);

            this.nHops = opts.nHops;
            this.bandwidthPerHop_Hz = opts.bandwidthPerHop_Hz;
            this.guardTime_s = opts.guardTime_s;
            this.transmissionTotTime = opts.transmissionTotTime;
        end

        function dataIQ = generateTransmission(this)
            totalSamples = max(1, round(this.transmissionTotTime * this.transmissionRate_Hz));
            guardSamples = round(this.guardTime_s * this.transmissionRate_Hz);
            payloadSamples = max(1, totalSamples - guardSamples * max(this.nHops - 1, 0));
            hopSamples = max(1, floor(payloadSamples / this.nHops));

            hopCenters = linspace( ...
                -this.bandwidth_Hz / 2 + this.bandwidthPerHop_Hz / 2, ...
                this.bandwidth_Hz / 2 - this.bandwidthPerHop_Hz / 2, ...
                this.nHops);
            hopCenters = hopCenters(randperm(numel(hopCenters)));

            segments = cell(this.nHops, 1);
            for hopIdx = 1:this.nHops
                n = (0:hopSamples - 1).';
                segments{hopIdx} = exp(2j * pi * hopCenters(hopIdx) / this.transmissionRate_Hz .* n);
            end

            dataIQ = segments{1};
            for hopIdx = 2:this.nHops
                dataIQ = [dataIQ; zeros(guardSamples, 1); segments{hopIdx}]; %#ok<AGROW>
            end
            if numel(dataIQ) < totalSamples
                dataIQ = [dataIQ; zeros(totalSamples - numel(dataIQ), 1)];
            else
                dataIQ = dataIQ(1:totalSamples);
            end
        end
    end
end
