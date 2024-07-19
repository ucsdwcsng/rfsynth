"""
Utils module for the rfsynth package. This module contains helper functions
"""

import logging
import concurrent.futures
import os
import sys
from pathlib import Path
import json
import shutil
import subprocess

from rfsynth.otatestbed.realTimeTestbed import real_time_tx_loop, load_config_json
from rfsynth.otatestbed.report_utils import (
    offset_ground_truth,
    translate_modulation,
    # add_no_modification_label,
)


def setup_logger(
    log_path: str = "./logs", file_name: str = "rfsynth.log", loglevel=logging.INFO
):
    """
    Sets up an instance of the logger for the rfsynth package. This logger will
    be used by all the modules in the package.

    :param log_path: Optional path to the directory where the log file will be stored.
    :type log_path: str or "./logs"

    :param file_name: Optional name of the log file
    :type file_name: str or "rfsynth.log"

    :param loglevel: Optional logging level
    :type loglevel: int or logging.INFO

    :return: None

    """
    logFormatter = logging.Formatter(
        "%(asctime)s [%(threadName)-12.12s] [%(name)s] [%(levelname)-5.5s] \
        %(message)s"
    )
    rootLogger = logging.getLogger()
    rootLogger.setLevel(loglevel)

    # Make directory if it does not exist.
    Path(f"{log_path}").mkdir(parents=True, exist_ok=True)

    fileHandler = logging.FileHandler("{0}/{1}".format(log_path, file_name))
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(stream=sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)


def real_time_transmit(start_time: float, tx_config_file: str):
    """
    Performs a real time transmission of the data provided by the config file.
    The transmission starts when the system time equals start_time

    :param start_time: The system time at which the transmission should start
    :type start_time: float

    :param tx_config_file: The name of the config file
    :type tx_config_file: str

    :return: None

    """
    config_json = load_config_json(tx_config_file)
    num_transmitters = len(config_json["radios"])
    logging.info(f"Starting with {num_transmitters} radios")

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = list()
        for idx in range(num_transmitters):
            p = executor.submit(real_time_tx_loop, tx_config_file, idx, 0, start_time)
            futures.append(p)

        for future in concurrent.futures.as_completed(futures):
            print(future.result())


def get_config_dicts(json_file: str):
    """
    Loads the config file and returns a dictionary

    :param json_file: The name of the config file
    :type json_file: str

    :return: The dictionary containing the config file
    :rtype: dict
    """
    try:
        f = open(json_file)
    except:
        logging.error("Error: Cannot load config file, exiting")
        raise

    cnfg_dict = json.load(f)

    return cnfg_dict


def setup_compressedE(data_file: str, folder: str = "/tmp/"):
    unzip_command = ["unzip", "-o", data_file, "-d", folder]
    proc_hdl = run_command(unzip_command, os.path.abspath("./"))
    logging.info("Data loaded")

    output_list = list()
    for k in proc_hdl.stdout.split():
        print("unzip output", k)
        if k[-3:] == "csv":
            # Move CSV to default name
            fixed_compressedE_file = f"{folder}compressedE_auto_energy_meta.csv"

            mv_command = ["mv", k, fixed_compressedE_file]
            proc_hdl = run_command(mv_command, os.path.abspath("../"))
            output_list.append(fixed_compressedE_file)
            print("k", output_list)
        elif k[-1] != ":":
            output_list.append(k)
            print("k", output_list)
    return output_list


def exception_complainer(e):
    """
    Helper function to log exceptions

    :param e: The exception to log
    :type e: Exception

    :return: None

    """
    try:
        logging.error(f"Exception: {e}")
    except:
        pass


def offset_and_upload_ground_truth(gt_filename: str, offset_time, commit_hash, idx):
    """
    Create a record of the ground truth and write it to a file

    :param gt_filename: The name of the ground truth file
    :type gt_filename: str

    :param offset_time: The time to offset the ground truth by
    :type offset_time: float

    :param commit_hash: The commit hash of the current experiment
    :type commit_hash: str

    :param idx: The index of the current experiment
    :type idx: int

    :return: The path to the ground truth file
    :rtype: str
    """
    gt_dict = offset_ground_truth(gt_filename, offset_time)
    gt_dict = translate_modulation(gt_dict)
    # gt_dict = add_no_modification_label(gt_dict)

    # Dump gt
    gt_filename = f"compressedE_gt_{commit_hash}_test_{idx+1}.json"
    gt_path = "/tmp/"
    with open(f"{gt_path}{gt_filename}", "w") as outfile:
        json.dump(gt_dict, outfile, indent=4)
    # upload gt
    try:
        return f"/tmp/{gt_filename}", gt_dict
    except Exception as e:
        exception_complainer(e)


def replace_files(filename1: str, filename2: str):
    """Copy contents filename1 into filename2. Overwrites filename2

    :param filename1: The name of the file to copy
    :type filename1: str

    :param filename2: The name of the file to overwrite
    :type filename2: str

    :return: 0 if the files are the same
    :rtype: int
    """

    if filename1 == filename2:
        return 0

    with open(filename1, "+rb") as input, open(filename2, "+wb") as output:
        shutil.copyfileobj(input, output)


def run_command(
    command: list, cwd: str = None, stdoutp=subprocess.PIPE, sterrp=subprocess.PIPE
):
    """
    Run a command and return the process handle

    :param command: The command to run
    :type command: list

    :param cwd: The current working directory
    :type cwd: str

    :param stdoutp: The stdout pipe
    :type stdoutp: subprocess.PIPE

    :param sterrp: The stderr pipe
    :type sterrp: subprocess.PIPE

    :return: The process handle
    :rtype: int
    """
    # proc_hdl = subprocess.run(command,capture_output=True, text=True, cwd = cwd, check=True)
    proc_hdl = subprocess.run(
        command,
        stdout=stdoutp,
        stderr=sterrp,
        universal_newlines=True,
        cwd=cwd,
        check=True,
    )
    return proc_hdl
