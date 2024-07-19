import json
import copy
import sys
import os
from absl import flags
from timeit import timeit
import numpy as np
from numpy.matlib import repmat
from scipy import signal
import matplotlib.pyplot as plt
from config_file_parser import tx_config_parse, rx_config_parse
from receiver import Receiver
from transmitter import Transmitter
from preamble import Preamble
from fractions import Fraction
import time
import logging

# decorater definition used for timing methods
def timeit(f):
    try:
        def timed(self):
            ts = time.time()            
            result = f(self)
            te = time.time()
            print(f'{f.__qualname__} took: {te-ts:4.2f} seconds')            
            return result        
        return timed
    except:
        pass

class OtaTestbed:
    def __init__(self,rx_config_file,tx_config_file):
        # Load radio configurations
        self.rx_config = self.load_config_json(rx_config_file)
        self.tx_config = self.load_config_json(tx_config_file)        

        # Parse configs for possible errors, just checks no effect
        rx_config_parse(self.rx_config)
        tx_config_parse(self.tx_config)         

        # General simulation parameters
        self.extract_params_from_json()
        # self.preamble_on = 40 # on-time (ms)
        self.preamble_seeds = np.random.randint(0,2**32,self.num_channels_tx)      

        # Instantiate all radios
        self.receivers = self.initialize_receivers()
        self.transmitters = self.initialize_transmitters() 

        # Each tx/rx pair gets its own preamble object to maintain state between that pair
        self.preambles = []
        self.preambles_to_idxs_dict = {}
        self.idxs_to_preambles_dict = {}
        for n,receiver in enumerate(self.receivers):
            for m in range(receiver.num_channels):
                tx_ch_idx = 0
                for i,transmitter in enumerate(self.transmitters):
                    for j in range(transmitter.num_channels):
                        idxs = (i,j,n,m)
                        preamble = Preamble(self.preamble_on, self.preamble_seeds[tx_ch_idx], self.fs, idxs)                      
                        tx_ch_idx += 1
                        self.preambles_to_idxs_dict[preamble] = idxs # tracks tx_num,tx_ch_num,rx_num,rx_ch_num for each preamble
                        self.idxs_to_preambles_dict[idxs] = preamble
                        self.preambles.append(preamble)

    def extract_params_from_json(self):
        self.preamble_on = self.tx_config['preambleOnTimeMs']
        self.fs = self.rx_config['radios'][0]['sampleRate']
        self.save_dir = self.rx_config['save_dir']
        self.num_rx = len(self.rx_config['radios'])
        self.num_tx = len(self.tx_config['radios'])

        self.num_channels_tx = 0
        for radio in self.tx_config['radios']:
            self.num_channels_tx += len(radio['channels'])

        self.num_channels_rx = 0
        for radio in self.rx_config['radios']:
            self.num_channels_rx += len(radio['channels'])

        self.num_channels = self.num_channels_tx + self.num_channels_rx   

    def read_from_file(self,filepath):
        data = np.fromfile(filepath,np.complex64).astype(np.complex128)
        return data

    def write_to_file(self,filepath, data):
        with open(filepath, 'wb') as f:
            np.array(data, dtype=np.complex64).tofile(f)
        return

    @timeit
    def collect(self):        
        self.print_all_radio_settings()

        # Setup all preamble objects and insert preambles on data
        tx_signals = []
        for n,receiver in enumerate(self.receivers):
            for m in range(receiver.num_channels):                
                for i,transmitter in enumerate(self.transmitters):
                    for j in range(transmitter.num_channels):
                        iq_filepath = transmitter.filepaths[j]
                        data_to_tx = self.read_from_file(iq_filepath)
                        data_to_tx = (data_to_tx / np.max(np.abs(data_to_tx)) * 1)
                        preamble = self.idxs_to_preambles_dict[(i,j,n,m)] 
                        tx_signal = preamble.insert(data_to_tx)
                        if n == 0:
                            tx_signals.append(tx_signal / np.max(np.abs(tx_signal)) * 0.8)

        # Place data into vector sources
        tx_ch_idx = 0
        for i,transmitter in enumerate(self.transmitters):
            for j in range(transmitter.num_channels):
                transmitter.set_single_channel_data(tx_signals[tx_ch_idx],j)
                tx_ch_idx += 1

        # Begin recording        
        for i,receiver in enumerate(self.receivers):
            receiver.start()
        print("Receiving has begun...")

        time.sleep(0.5)
        # Begin transmitting        
        for i,transmitter in enumerate(self.transmitters):
            transmitter.start()
        print("Transmitting has begun...")        

        # Stop all transmitters and receivers        
        for receiver in self.receivers:
            receiver.wait()
            receiver.stop()
        print("Stopped receiving...")

        for transmitter in self.transmitters:
            # transmitter.wait()
            transmitter.stop()
        print("Stopped transmitting...")

        # Slice the received signals at the front and back using preambles and meta
        sliced_signals = []
        for n,receiver in enumerate(self.receivers):
            for m in range(receiver.num_channels):
                for i,transmitter in enumerate(self.transmitters):
                    for j in range(transmitter.num_channels):
                        preamble = self.idxs_to_preambles_dict[(i,j,n,m)]
                        #sliced_signals.append(preamble.remove(receiver.get_single_channel_data(m)))
                        sliced_signal = preamble.remove(receiver.get_single_channel_data(m))
                        sliced_signals.append(sliced_signal)

                        if sliced_signal is not None:
                            # Update metadata and save everything
                            iq_filename = os.path.basename(transmitter.filepaths[j])
                            metadata_filepath = transmitter.metadata_files[j]
                            metadata_filename = os.path.basename(metadata_filepath)
                           
                            # Load metadata json
                            with open(metadata_filepath,'r') as f:
                                metadata_json = json.load(f)

                            # Get updated metadata
                            updated_metadata_json = self.update_metadata(metadata_json,n,m,i,j) 

                            # Get new filenames
                            slice_filename = "Tx"+str(i)+"-"+str(j)+"_Rx"+str(n)+"-"+str(m)+"_"+iq_filename
                            new_metadata_filename = "Tx"+str(i)+"-"+str(j)+"_Rx"+str(n)+"-"+str(m)+"_"+metadata_filename
            
                            try:
                                # Save updated metadata
                                with open(os.path.join(self.save_dir,new_metadata_filename),'w') as f:
                                    json.dump(updated_metadata_json,f, ensure_ascii=False, indent=4)

                                # Save sliced signal
                                self.write_to_file(os.path.join(self.save_dir,slice_filename),sliced_signal)
                            except Exception as e:
                                print(f'\nCould not save files to provided directory\n{e}\n')
                            

    def load_config_json(self,config_filename):
        with open(config_filename,'r') as f:
            config_json = json.load(f)

        return config_json

    def update_metadata(self,metadata,
                        receiver_num,
                        receiver_channel_num,
                        transmitter_num,
                        transmitter_channel_num):

        updated_metadata = copy.deepcopy(metadata)
        receiver = copy.deepcopy(self.rx_config['radios'][receiver_num])
        receiver_channel = copy.deepcopy(receiver['channels'][receiver_channel_num])
        transmitter = copy.deepcopy(self.tx_config['radios'][transmitter_num])
        transmitter_channel = copy.deepcopy(transmitter['channels'][transmitter_channel_num])

        # Remove 'channels' key from config copies, replace with single channel
        del receiver['channels']
        del transmitter['channels']
        receiver['channel'] = receiver_channel
        transmitter['channel'] = transmitter_channel

        # Update siggen metadata
        updated_metadata['receiver_config'] = receiver
        updated_metadata['transmitter_config'] = transmitter        
        return updated_metadata

    def initialize_receivers(self):
        receivers = []
        for radio_config_d in self.rx_config['radios']:
            receiver = Receiver(radio_config_d)
            receivers.append(receiver)
        return receivers

    def initialize_transmitters(self):
        transmitters = []
        for radio_config_d in self.tx_config['radios']:
            transmitter = Transmitter(radio_config_d)
            transmitters.append(transmitter)
        return transmitters

    def print_all_radio_settings(self):
        for i, transmitter in enumerate(self.transmitters):
            print("TRANSMITTER",i)
            transmitter.print_settings()

        for i, receiver in enumerate(self.receivers):
            print("RECEIVER", i)
            receiver.print_settings()

    @timeit
    def show_debug_plots(self):
        ## Visualizations
        for preamble in self.preambles:
            try:                
                preamble.plot_debug_xcorr(self.preambles_to_idxs_dict[preamble])
                preamble.plot_debug_tx_time(self.preambles_to_idxs_dict[preamble])
                preamble.plot_debug_rx_time(self.preambles_to_idxs_dict[preamble])
                # preamble.plot_debug_spectrograms(self.preambles_to_idxs_dict[preamble])
                plt.show()
            except:
                print('A problem occured while plotting.')

if __name__ == "__main__":
        
    flags.DEFINE_string("rx_config_file", None, "RX config file to use")
    flags.DEFINE_string("tx_config_file", None, "TX config file to use")

    FLAGS = flags.FLAGS
    FLAGS(sys.argv)

    print("Selected RX config file:",FLAGS.rx_config_file)
    print("Selected TX config file:",FLAGS.tx_config_file)

    rx_config_file = FLAGS.rx_config_file
    tx_config_file = FLAGS.tx_config_file
    rx_config_file = 'configs/rx_config_scenario1.json'
    tx_config_file = 'configs/tx_config_scenario1.json'
    # import pdb; pdb.set_trace()
    otaTestbed = OtaTestbed(rx_config_file,tx_config_file)
    
    otaTestbed.collect()
    # import pdb; pdb.set_trace()
    otaTestbed.show_debug_plots()
