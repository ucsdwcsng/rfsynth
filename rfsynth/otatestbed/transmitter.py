from rfsynth.otatestbed.transmitter_flowgraph import transmitter_flowgraph
import numpy as np
import json
import pandas as pd
import logging
import pdb
import time

logger = logging.getLogger(__name__)


class Transmitter:
    def __init__(self, radio_config_d):
        # Pull radio settings from the config dictionary
        self.address = radio_config_d["addrs"][0]
        self.clock_rate = radio_config_d["masterClockRate"]
        self.sample_rate = radio_config_d["sampleRate"]
        self.num_channels = len(radio_config_d["channels"])
        self.subdev_spec = radio_config_d["subdevSpec"]
        # self.num_seconds_receive = radio_config_d['numSecondsReceive']

        # Initialze radio flowgraph
        self.tb = transmitter_flowgraph(
            address=self.address,
            clock_rate=self.clock_rate,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels,
            subdev_spec=self.subdev_spec,
        )

        # Configure individual channels on the flowgraph
        self.filepaths = []
        self.metadata_files = []
        for channel_num, channel_config_d in enumerate(radio_config_d["channels"]):
            # Pull antenna settings from the channel config dictionary
            antenna = channel_config_d["antenna"]
            gain = channel_config_d["gain"]
            center_freq = channel_config_d["IQSTREAM_Params"]["frequency"]

            # Configure the channel settings
            self.tb.configure_channel(antenna, gain, center_freq, channel_num)
            # Set time to host-time
            self.tb.set_time_now()

            self.filepaths.append(channel_config_d["IQSTREAM_Params"]["file"])
            self.metadata_files.append(channel_config_d["IQSTREAM_Params"]["metadata"])

    def set_time_now(self):
        self.tb.set_time_now()

    def get_time_difference(self):
        return self.tb.get_time_difference()

    def timed_start(self, time_start):
        self.tb.timed_start(time_start)

    def timed_tune_channel(self, center_freq, cmd_time, channel_idx):
        self.tb.timed_tune_channel(center_freq, cmd_time, channel_idx)

    def start(self):
        self.tb.start()

    def wait(self):
        self.tb.wait()

    def stop(self):
        self.tb.stop()
        self.tb.reset_flowgraph()

    def real_time_transmit_loop(self, transmitter_idx, channel_idx, start_time):

        meta_file = self.metadata_files[channel_idx]
        df = self.read_meta_file(meta_file)
        """
        report_type                             energy
        instance_name                       wifi_1 T_1
        time_start                                 0.0
        time_stop                              0.00136
        freq_lo                             2403780000
        freq_hi                             2420220000
        timeLength_s                           0.00136
        bandwidth_Hz                          16440000
        signal_index                                 1
        tx_radio                                     1
        iq_filename      /tmp/testPolaroid_wifi_1.32cf
        Name: 0, dtype: object
        """
        num_tx_es = 0

        # Consider fixing this prev filename thing?
        prev_filename = ""
        center_freq_prev = 0
        prev_time_stop: float = -1
        for row_idx, row in df.iterrows():

            st_time = time.time()
            # Check if this is for you
            if row.tx_radio != transmitter_idx + 1:
                continue

            # Check if previous transmission is done
            if prev_time_stop + 0.0070 > row.time_start:
                logger.warning(
                    f"Tx {transmitter_idx}.Chan {channel_idx} Skipping energy {row_idx} because previous energy is still transmitting"
                )
                continue

            center_freq = (row.freq_lo + row.freq_hi) / 2
            if center_freq_prev != center_freq:
                self.timed_tune_channel(
                    center_freq, start_time + row.time_start, channel_idx
                )
                center_freq_prev = center_freq

            # TODO: configure gain

            # configure file
            if prev_filename != row.iq_filename:
                self.set_single_channel_data_from_file(row.iq_filename, channel_idx)
                prev_filename = row.iq_filename
            mid_time = time.time()
            # start and wait

            self.timed_start(start_time + row.time_start)
            self.wait()
            self.stop()
            logger.debug(
                f"One timed loop: {time.time() - st_time}, mid_time: {mid_time-st_time}"
            )
            prev_time_stop = row.time_start + row.timeLength_s

            num_tx_es += 1

        logger.info(
            f"Tx {transmitter_idx}.Chan {channel_idx} Transmitted {num_tx_es} energies"
        )

    def set_all_channel_data(self):
        for channel_num in range(self.num_channels):
            iq_filepath = self.filepaths[channel_num]
            self.set_single_channel_data_from_file(iq_filepath, channel_num)

    def set_single_channel_data_from_file(self, iq_filepath, channel_num):
        data_to_tx = self.read_from_file(iq_filepath)
        logger.warning("Transmit code is normalizing data magnitudes")
        data_to_tx = data_to_tx / np.max(np.abs(data_to_tx)) * 1
        self.set_single_channel_data(data_to_tx, channel_num)

    def set_single_channel_data(self, data, channel_num):
        self.tb.set_vector_source_data(data, channel_num)
        return

    def read_from_file(self, filepath):
        data = np.fromfile(filepath, np.complex64).astype(np.complex128)
        return data

    def read_meta_file(self, meta_file):
        df = pd.read_csv(meta_file)
        return df

    """
    def get_all_channel_data(self):
        channel_data_list = [np.asarray(self.tb.get_channel_data(i)) for i in range(self.num_channels)]
    """

    def rx(self):
        pass

    def tx(self):
        pass

    def print_settings(self):
        self.tb.print_radio_settings()
        for channel_num in range(self.num_channels):
            self.tb.print_channel_settings(channel_num)


if __name__ == "__main__":
    tx_config_file = "tx_radio_config.json"
    with open(tx_config_file, "r") as f:
        tx_config = json.load(f)

    print(tx_config["radios"])
    radio_config_d = tx_config["radios"][0]

    transmitter = Transmitter(radio_config_d)
    # transmitter.start()
    # transmitter.wait()
    transmitter.stop()
    transmitter.print_settings()
