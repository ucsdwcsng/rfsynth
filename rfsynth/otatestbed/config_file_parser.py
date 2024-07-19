import os


def tx_config_parse(tx_config):
    check_num_radios(tx_config)
    check_num_channels(tx_config)
    check_antenna_type(tx_config)
    check_gain(tx_config)
    enforce_same_sample_rate(tx_config)

def rx_config_parse(rx_config):
    check_save_dir(rx_config)
    check_num_radios(rx_config)
    check_num_channels(rx_config)
    check_antenna_type(rx_config)
    check_gain(rx_config)
    enforce_same_sample_rate(rx_config)
    

    for radio in rx_config['radios']:
        for channel in radio['channels']:
            pass

def check_num_radios(config):
    num_radios = len(config['radios'])
    if num_radios < 1:
        raise ValueError(f'No radios were listed in the config')

def check_num_channels(config):
    radios = config['radios']
    for radio in radios:
        num_channels = len(radio['channels'])
        if num_channels < 1:
            raise ValueError(f'No channels were specified for one of the radios')
        if num_channels > 4:
            raise ValueError(f'Too many channels ({num_channels}) were specified for one of the radios')

def check_antenna_type(config):
    antenna_types = {'TX/RX','RX2'}
    radios = config['radios']
    for radio in radios:
        for channel in radio['channels']:
            antenna = channel['antenna']
            if antenna not in antenna_types:
                raise ValueError(f'Invalid antenna type was given ({antenna}). Should be one of {antenna_types} ')    

def check_gain(config):
    radios = config['radios']
    for radio in radios:
        for channel in radio['channels']:
            gain = channel['gain']
            if gain < 0.0 or gain > 1.0:
                raise ValueError(f'Invalid gain was given ({gain}). Should be a normalized gain between 0.0 and 1.0')

def check_save_dir(rx_config):
    save_dir = rx_config['save_dir']
    if not os.path.exists(save_dir):
        raise FileExistsError(f'Save directory {save_dir} in rx_config_file does not exist')    
    if not os.access(save_dir, os.W_OK | os.X_OK):
        raise PermissionError(f'Save directory {save_dir} in rx_config_file is not accessible')

def enforce_same_sample_rate(config):
    radios = config['radios']
    sample_rates = set()
    for radio in radios:
        sample_rates.add(radio['sampleRate'])

    if len(sample_rates) > 1: # If there is more than one unique sample rate
        raise ValueError(f'There should only be one sample rate used for all radios. The sample rates given are {sample_rates}')







