#!/usr/bin/env python
"""
Script to transmit compressedE files
"""
import argparse
import logging
import time
import concurrent.futures
import yaml
import zmq

from rfsynth.utils import (
    real_time_transmit,
    setup_logger,
    setup_compressedE,
    offset_and_upload_ground_truth,
    replace_files,
    run_command,
)

__author__ = "Raghav Subbaraman"
__copyright__ = "Copyright 2022, Regents of the University of California"
__credits__ = ["Raghav Subbaraman"]
__license__ = ""
__version__ = "0.0"
__maintainer__ = "Raghav Subbaraman"
__email__ = "rsubbaraman@eng.ucsd.edu"
__status__ = "Development"


def get_parser():
    """
    Get parser object for script compressedE_tx.py

    :return: Parser object
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION]", description="Configure compressedE parameters"
    )
    parser.add_argument(
        "--data",
        type=str,
        default="../config/automator/compressedE_test.yaml",
        help="Data package from compressed engine",
    )
    parser.add_argument(
        "--txconfig",
        type=str,
        default="",
        help="Tx frontend configuration",
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default="/tmp/ground_truth_print.json",
        help="Path to save",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{parser.prog} version " + __version__,
    )
    return parser


def get_config_keys(config_filename: str):
    """
    Extracts the config keys from the provided config file

    :param config_filename: The name of the config file
    :type config_filename: str

    :return: A list of config keys
    :rtype: list
    """
    with open(config_filename, "r") as stream:
        try:
            op_dict = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    return op_dict["config_keys"]


class ZmqPubServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 62002):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)  # REP (REPLY) socket for the server
        self.socket.bind(f"tcp://{host}:{port}")

    def __del__(self):
        self.socket.close()
        self.context.term()

    def publish_message(self, message_dict):
        # Send reply back to client
        self.socket.send_json(message_dict)


class ZmqSubClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 62002):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{host}:{port}")
        self.socket.subscribe("")

    def receive_message(self):
        # Receive a request from client
        message = self.socket.recv_json()
        return message


def energy_broadcaster(gt_dict: dict):
    # find signal reports

    zmq_server = ZmqPubServer()

    for item in gt_dict["reports"]:
        try:
            if item["report_type"] == "signal" or item["report_type"] == "energy":
                # get time start
                time_start = item["time_start"]

                # wait until time_start
                while time.time() < time_start:
                    time.sleep(0.001)
                    pass
                zmq_server.publish_message(item)

            else:
                pass
        except Exception as e:
            logging.error(f"{e}")
            pass


def main():
    """
    Entrypoint for rfsynth
    """
    parser = get_parser()
    args = parser.parse_args()
    print(args)

    setup_logger(file_name="compressedE_test.log")

    # Reason for looping over keys: To allow for multiple compressedE files to be
    # transmitted simultaneously
    for key in get_config_keys(args.config):
        # This is the same reason for using this process pool executor
        with concurrent.futures.ProcessPoolExecutor() as process_pool:
            output_filenames = setup_compressedE(args.data)
            # Print the compressedE frontend configuration for debugging
            logging.debug("frontend cfg", args.txconfig)

            # Make the start time 5 seconds from now
            start_time = time.time() + 5
            # create a process to transmit the compressedE file
            compressedE_proc = process_pool.submit(
                real_time_transmit, start_time, args.txconfig
            )

            # loop over the output filenames and upload the ground truth
            for filename in output_filenames:
                if filename[-4:] == "json":
                    gt_report, gt_dict = offset_and_upload_ground_truth(
                        filename, start_time, "PLRD_TEST", args.index
                    )
                    replace_files(gt_report, args.path)

            # put energy_broadcaster into a process
            energy_broadcaster_proc = process_pool.submit(energy_broadcaster, gt_dict)

            # Print the process info
            # ERROR: This is blocking! TODO: Should put in an array and print later
            logging.debug(f"Process info: {compressedE_proc.result()}")

            # Wait till energy broadcaster is done
            logging.debug(f"Process info: {energy_broadcaster_proc.result()}")

            for file_n in output_filenames:
                if file_n[-4:] == "32cf":
                    logging.info(f"removing {file_n}")
                    rm_command = ["rm", file_n]
                    run_command(rm_command, "./")


if __name__ == "__main__":
    main()
