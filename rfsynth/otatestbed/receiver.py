from rfsynth.otatestbed.receiver_flowgraph import receiver_flowgraph
import numpy as np
import json


class Receiver:
    def __init__(self, radio_config_d):
        # Pull radio settings from the config dictionary
        self.address = radio_config_d["addrs"][0]
        self.clock_rate = radio_config_d["masterClockRate"]
        self.sample_rate = radio_config_d["sampleRate"]
        self.num_channels = len(radio_config_d["channels"])
        self.subdev_spec = radio_config_d["subdevSpec"]
        self.num_seconds_receive = radio_config_d["numSecondsReceive"]

        # Initialze radio flowgraph
        self.tb = receiver_flowgraph(
            address=self.address,
            clock_rate=self.clock_rate,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels,
            subdev_spec=self.subdev_spec,
            num_seconds_receive=self.num_seconds_receive,
        )

        # Configure individual channels on the flowgraph
        for channel_num, channel_config_d in enumerate(radio_config_d["channels"]):
            # Pull antenna settings from the channel config dictionary
            antenna = channel_config_d["antenna"]
            gain = channel_config_d["gain"]
            center_freq = channel_config_d["IQSTREAM_Params"]["frequency"]

            # Configure the channel settings
            self.tb.configure_channel(antenna, gain, center_freq, channel_num)

    def start(self):
        self.tb.start()

    def wait(self):
        self.tb.wait()

    def stop(self):
        self.tb.stop()

    def get_single_channel_data(self, channel_num):
        channel_data = self.tb.get_vector_sink_data(channel_num)
        channel_data = np.asarray(channel_data)
        channel_data = channel_data.astype(dtype=np.complex64)
        return channel_data

    def get_all_channel_data(self):
        channel_data_list = [
            np.asarray(self.tb.get_vector_sink_data(i), dtype=np.complex64)
            for i in range(self.num_channels)
        ]
        return channel_data_list

    def rx(self):
        pass

    def tx(self):
        pass

    def print_settings(self):
        self.tb.print_radio_settings()
        for channel_num in range(self.num_channels):
            self.tb.print_channel_settings(channel_num)


if __name__ == "__main__":
    rx_config_file = "rx_radio_config.json"
    with open(rx_config_file, "r") as f:
        rx_config = json.load(f)

    print(rx_config["radios"])
    radio_config_d = rx_config["radios"][0]

    receiver = Receiver(radio_config_d)
    receiver.start()
    receiver.wait()
    receiver.stop()
    data = receiver.get_all_channel_data()
    print(len(data), len(data[0]), len(data[1]))
    receiver.print_settings()
