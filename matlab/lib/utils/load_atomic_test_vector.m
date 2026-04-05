function vec = load_atomic_test_vector(pathIn)
raw = jsondecode(fileread(pathIn));
vec = raw;

if isfield(raw, 'payload')
    payload = raw.payload;
    if isfield(payload, 'symbols_real')
        vec.payload.symbols = complex(double(payload.symbols_real), double(payload.symbols_imag));
    end
    if isfield(payload, 'data_symbols_real')
        vec.payload.data_symbols = complex(double(payload.data_symbols_real), double(payload.data_symbols_imag));
    end
    if isfield(payload, 'pilot_symbols_real')
        vec.payload.pilot_symbols = complex(double(payload.pilot_symbols_real), double(payload.pilot_symbols_imag));
    end
    if isfield(payload, 'samples_real')
        vec.payload.samples = complex(double(payload.samples_real), double(payload.samples_imag));
    end
    if isfield(payload, 'message_real')
        vec.payload.message = complex(double(payload.message_real), double(payload.message_imag));
    end
    scalarish = {'symbol_indices', 'bits', 'message_bits', 'access_address_bits', 'hop_centers_hz', 'spread_code', 'scrambler_initialization'};
    for idx = 1:numel(scalarish)
        key = scalarish{idx};
        if isfield(payload, key)
            vec.payload.(key) = payload.(key);
        end
    end
end
