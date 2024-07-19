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


class uhd_receive(gr.top_block):

    def __init__(self,addr):
        gr.top_block.__init__(self, "Not titled yet")

        ##################################################
        # Variables
        ##################################################
        self.save_path = save_path = "/mnt/ext_hdd_18tb/ota_testing/test.bin"
        self.samp_rate = samp_rate = 200e6/2
        self.rx_gain = rx_gain = 0.8
        self.num_seconds = num_seconds = 1
        self.device_address = device_address = addr
        self.center_freq = center_freq = 4.1e9

        ##################################################
        # Blocks
        ##################################################
        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join((device_address, "")),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_center_freq(center_freq, 0)
        self.uhd_usrp_source_0.set_normalized_gain(rx_gain, 0)
        self.uhd_usrp_source_0.set_antenna('TX/RX', 0)
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_time_unknown_pps(uhd.time_spec())
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex*1, int(samp_rate*num_seconds))
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex*1, save_path, False)
        self.blocks_file_sink_0.set_unbuffered(False)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_head_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_head_0, 0))


    def get_save_path(self):
        return self.save_path

    def set_save_path(self, save_path):
        self.save_path = save_path
        self.blocks_file_sink_0.open(self.save_path)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_head_0.set_length(int(self.samp_rate*self.num_seconds))
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_rx_gain(self):
        return self.rx_gain

    def set_rx_gain(self, rx_gain):
        self.rx_gain = rx_gain
        self.uhd_usrp_source_0.set_normalized_gain(self.rx_gain, 0)

    def get_num_seconds(self):
        return self.num_seconds

    def set_num_seconds(self, num_seconds):
        self.num_seconds = num_seconds
        self.blocks_head_0.set_length(int(self.samp_rate*self.num_seconds))

    def get_device_address(self):
        return self.device_address

    def set_device_address(self, device_address):
        self.device_address = device_address

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq
        self.uhd_usrp_source_0.set_center_freq(self.center_freq, 0)





def main(top_block_cls=uhd_receive, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    tb.wait()


if __name__ == '__main__':
    main()
