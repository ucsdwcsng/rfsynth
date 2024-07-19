#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.8.5.0-rc1

from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
import logging


class transmitter_flowgraph(gr.top_block):
    def __init__(self, address, clock_rate, sample_rate, num_channels, subdev_spec):
        gr.top_block.__init__(self, "Not titled yet")

        # Radio settings
        self.address = address
        self.clock_rate = clock_rate
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.subdev_spec = subdev_spec

        # Instantiate sink block
        self.uhd_usrp_sink = uhd.usrp_sink(
            ",".join((str(address), "", "master_clock_rate=" + str(clock_rate))),
            uhd.stream_args(
                cpu_format="fc32",
                args="",
                channels=list(range(0, num_channels)),
            ),
            "",
        )
        self.uhd_usrp_sink.set_subdev_spec(subdev_spec, 0)
        self.uhd_usrp_sink.set_clock_rate(clock_rate, uhd.ALL_MBOARDS)
        self.uhd_usrp_sink.set_samp_rate(sample_rate)
        self.uhd_usrp_sink.set_time_unknown_pps(uhd.time_spec())

        # Store vector source blocks for future access
        self.vector_source_blocks = {}

    def configure_channel(self, antenna, gain, center_freq, channel_num):
        # Configure antenna settings, fc, and gain
        self.uhd_usrp_sink.set_antenna(antenna, channel_num)
        self.uhd_usrp_sink.set_normalized_gain(gain, channel_num)
        self.uhd_usrp_sink.set_center_freq(center_freq, channel_num)

        # Create vector source blocks
        vector_source_block = blocks.vector_source_c((0, 0, 0), False, 1, [])

        # Head block: Not neeeded?
        # tx_head_block = blocks.head(gr.sizeof_gr_complex*1, int(100000))

        # Connect block to sink
        self.connect((vector_source_block, 0), (self.uhd_usrp_sink, channel_num))

        # Add block to class field for future access
        self.vector_source_blocks[channel_num] = vector_source_block
        # self.tx_head_blocks[channel_num] = tx_head_block

        return

    def set_vector_source_data(self, data, channel_num):
        self.vector_source_blocks[channel_num].set_data(data)

        # self.tx_head_blocks[channel_num].reset()
        # self.tx_head_blocks[channel_num].set_length(len(data))
        # self.tx_head_blocks[channel_num].reset()

        return

    def reset_flowgraph(self):
        # Purge items in USRP buffer
        # TODO: check if this is needed for vector source
        # logging.debug("resetting streamer")
        # stream_args = uhd.stream_args(
        #     cpu_format="fc32",
        #     channels=list(range(0,self.num_channels)),
        #     )
        # self.uhd_usrp_sink.set_stream_args(stream_args)

        logging.debug("rewinding vector source block")
        # Rewind vector source blocks
        for channel_num in range(self.num_channels):
            self.vector_source_blocks[channel_num].rewind()

    def set_time_now(self):
        time_start = time.time()
        self.uhd_usrp_sink.set_time_now(uhd.time_spec(time_start), uhd.ALL_MBOARDS)
        # Setting takes ~2.2 ms -> Jitter?
        # logging.debug(f"Set Time Zero: Time elapsed = {time.time() - time_start}")
        return time_start

    def get_time_difference(self):
        time_now = self.uhd_usrp_sink.get_time_now()
        cpu_time = time.time()
        return cpu_time - time_now.get_real_secs()

    def timed_start(self, time_start):
        self.uhd_usrp_sink.set_start_time(uhd.time_spec_t(time_start))
        self.start()

    def timed_tune_channel(self, center_freq, cmd_time, channel_idx):
        self.uhd_usrp_sink.set_command_time(uhd.time_spec(cmd_time))
        self.uhd_usrp_sink.set_center_freq(center_freq, channel_idx)
        self.uhd_usrp_sink.clear_command_time()

    def print_radio_settings(self):
        print("Radio Settings:")
        print("IP Address:", self.address)
        print("Master Clock Rate:", self.uhd_usrp_sink.get_clock_rate())
        print("Sampling Rate:", self.uhd_usrp_sink.get_samp_rate())
        print("Subdev Spec:", self.uhd_usrp_sink.get_subdev_spec())
        print("Number of Channels:", self.num_channels)
        print()
        return

    def print_channel_settings(self, channel_num):
        print("Channel", channel_num, "Settings:")
        print("Antenna:", self.uhd_usrp_sink.get_antenna(channel_num))
        print("Center Frequency:", self.uhd_usrp_sink.get_center_freq(channel_num))
        print("Normalized Gain:", self.uhd_usrp_sink.get_normalized_gain(channel_num))
        print()
        return
