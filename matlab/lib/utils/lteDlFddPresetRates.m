function [bandwidth_Hz, transmissionRate_Hz] = lteDlFddPresetRates(NDLRB)
%LTEDLFDDPRESETRATES Bandwidth and sample-rate map for narrow LTE presets.

    switch NDLRB
        case 6
            bandwidth_Hz = 1.4e6;
            transmissionRate_Hz = 1.92e6;
        case 15
            bandwidth_Hz = 3e6;
            transmissionRate_Hz = 3.84e6;
        case 25
            bandwidth_Hz = 5e6;
            transmissionRate_Hz = 7.68e6;
        case 50
            bandwidth_Hz = 10e6;
            transmissionRate_Hz = 15.36e6;
        case 75
            bandwidth_Hz = 15e6;
            transmissionRate_Hz = 23.04e6;
        case 100
            bandwidth_Hz = 20e6;
            transmissionRate_Hz = 30.72e6;
        otherwise
            error('lteDlFddPresetRates:UnsupportedNDLRB', 'Unsupported NDLRB=%d', NDLRB);
    end
end
