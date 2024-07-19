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
from rfsynth.otatestbed.config_file_parser import tx_config_parse, rx_config_parse
from rfsynth.otatestbed.receiver import Receiver
from rfsynth.otatestbed.transmitter import Transmitter
from rfsynth.otatestbed.preamble import Preamble
from fractions import Fraction
import time
import pandas as pd
import logging

from concurrent.futures import ProcessPoolExecutor, as_completed


def setup_logger(log_path, file_name):
    logFormatter = logging.Formatter(
        "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
    )
    rootLogger = logging.getLogger()
    fileHandler = logging.FileHandler("{0}/{1}".format(log_path, file_name))
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)


# decorater definition used for timing methods
def timeit(f):
    try:

        def timed(self):
            ts = time.time()
            result = f(self)
            te = time.time()
            print(f"{f.__qualname__} took: {te-ts:4.4f} seconds")
            return result

        return timed
    except:
        pass


def load_config_json(config_filename):
    with open(config_filename, "r") as f:
        config_json = json.load(f)

    return config_json


def initialize_transmitters(tx_config_file, tx_idx):
    tx_config = load_config_json(tx_config_file)

    idx = 0
    flag = 0
    for radio_config_d in tx_config["radios"]:
        if idx == tx_idx:
            transmitter = Transmitter(radio_config_d)
            transmitter.set_all_channel_data()
            flag = 1
            break
        else:
            idx += 1

    if flag:
        return transmitter
    else:
        return None


def real_time_tx_loop(tx_config_file, transmitter_idx, channel_idx, start_time):
    logging.info(f"Init Tx {transmitter_idx}")
    transmitter = initialize_transmitters(tx_config_file, transmitter_idx)
    transmitter.real_time_transmit_loop(transmitter_idx, channel_idx, start_time)
    return 0
    try:
        transmitter = initialize_transmitters(tx_config_file, transmitter_idx)
        transmitter.real_time_transmit_loop(transmitter_idx, channel_idx, start_time)
        return 0
    except Exception as e:
        logging.warning(f"Transmitter Index {transmitter_idx} is in error")
        logging.error(f"Exception {e}")
        return -1


if __name__ == "__main__":
    flags.DEFINE_string("tx_config_file", None, "TX config file to use")
    FLAGS = flags.FLAGS
    FLAGS(sys.argv)

    print("Selected TX config file:", FLAGS.tx_config_file)
    tx_config_file = FLAGS.tx_config_file

    setup_logger("./", "realTimeTestbed.log")
    logging.info(f"Log file: ./realTimeTestbed.log")

    config_json = load_config_json(tx_config_file)
    num_transmitters = len(config_json["radios"])
    logging.info(f"Starting with {num_transmitters} radios")

    with ProcessPoolExecutor() as executor:
        futures = list()
        start_time = time.time() + 10
        for idx in range(num_transmitters):
            p = executor.submit(real_time_tx_loop, tx_config_file, idx, 0, start_time)
            futures.append(p)

        for future in as_completed(futures):
            print(future.result())

    # import pdb; pdb.set_trace()
    # otaTestbed.show_debug_plots()
