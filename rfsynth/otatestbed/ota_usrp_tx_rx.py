import json
import time
import os
from uhd_receive_testing import uhd_receive
from uhd_transmit_testing import uhd_transmit

# Dummy parameters for development
save_dir = "/mnt/ext_hdd_18tb/ota_testing"
num_seconds = 5

rx_config_file = "rx_radio_config.json"
tx_config_file = "tx_radio_config.json"

# Load in rx config json
with open(rx_config_file,'r') as f:
    rx_config = json.load(f)

# Set up rx radios
rx_radios = []
for radio_config in rx_config['radios']:
    device_address = radio_config['addrs'][0] 
    samp_rate = radio_config['sampleRate']
    radio_name = radio_config['name']

    for channel in radio_config['channels']:
        rx_gain = channel['gain']
        center_freq = channel['IQSTREAM_Params']['frequency']
        channel_name = channel['name']
        save_file = str(radio_name) + str(channel_name) + ".bin"

        # Instantiate radio, set all parameters
        tb_receive = uhd_receive(addr="addr="+str(device_address))
        tb_receive.set_device_address("addr="+str(device_address))
        tb_receive.set_samp_rate(samp_rate)
        tb_receive.set_rx_gain(rx_gain)
        tb_receive.set_center_freq(center_freq)
        tb_receive.set_num_seconds(num_seconds)
        tb_receive.set_save_path(os.path.join(save_dir,save_file))
        rx_radios.append(tb_receive)

# Load in tx config json
with open(tx_config_file,'r') as f:
    tx_config = json.load(f)

# Set up tx radios
tx_radios = []
for radio_config in tx_config['radios']:
    device_address = radio_config['addrs'][0] 
    samp_rate = radio_config['sampleRate']
    radio_name = radio_config['name']

    for channel in radio_config['channels']:
        tx_gain = channel['gain']
        center_freq = channel['IQSTREAM_Params']['frequency']
        signal_filename = channel['IQSTREAM_Params']['filename']
        channel_name = channel['name']

        # Instantiate radio, set all parameters
        tb_transmit = uhd_transmit(addr="addr="+str(device_address))
        tb_transmit.set_device_address("addr="+str(device_address))
        tb_transmit.set_samp_rate(samp_rate)
        tb_transmit.set_tx_gain(tx_gain)
        tb_transmit.set_center_freq(center_freq)
        tb_transmit.set_signal_filename(signal_filename)
        tx_radios.append(tb_transmit)

# Will probably want to do the rest of this with multithreading in the future
# Begin receiving
print("Begin Receiving...")
for rx_radio in rx_radios:
    rx_radio.start()

time.sleep(1)
# Begin transmitting
print("Begin Transmitting...")
for tx_radio in tx_radios:
    tx_radio.start()

# Wait for and stop each transmitter
print("End Transmitting...")
for tx_radio in tx_radios:
    tx_radio.wait()
    tx_radio.stop()

# Wait for and stop each receiver
print("End Receiving...")
for rx_radio in rx_radios:
    rx_radio.wait()
    rx_radio.stop()

'''
print()
print("RX Radios:")
for radio in rx_radios:
    print(radio.get_device_address())
    print(radio.get_samp_rate())
    print(radio.get_rx_gain())
    print(radio.get_center_freq())
    print(radio.get_num_seconds())
    print(radio.get_save_path())

    #tb_receive = uhd_receive()
    #rx_radios.append(tb_receive)

print()
print("TX Radios:")
for radio in tx_radios:
    print(radio.get_device_address())
    print(radio.get_samp_rate())
    print(radio.get_tx_gain())
    print(radio.get_center_freq())
    print(radio.get_signal_filename())
'''

