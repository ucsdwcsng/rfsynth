#!/usr/bin/env python
"""
Tools to parse or edit report files
TODO: More description
"""
import argparse
from cgi import test
from cmath import polar
from dataclasses import asdict

import json
import pdb
import shutil
import subprocess
import logging
from typing import List, Optional
import sys
import os
import time
import concurrent.futures
import csv
from pathlib import Path
import pandas as pd
import traceback 
import re

logger = logging.getLogger(__name__)

__author__ = "Raghav Subbaraman"
__copyright__ = "Copyright 2022, Regents of the University of California"
__credits__ = ["Raghav Subbaraman"]
__license__ = ""
__version__ = "0.0"
__maintainer__ = "Raghav Subbaraman"
__email__ = "rsubbaraman@eng.ucsd.edu"
__status__ = "Development"


def offset_ground_truth(gt_filename: str, offset_time):

    f = open(gt_filename)
    gt_dict = json.load(f)

    output_reports = list()
    for item in gt_dict["reports"]:
        try:
            if item["report_type"] == "signal":
                item["time_start"] = item["time_start"] + offset_time
                item["time_stop"] = item["time_stop"] + offset_time
                item["reference_time"] = item["reference_time"] + offset_time
            elif item["report_type"] == "energy":
                item["time_start"] = item["time_start"] + offset_time
                item["time_stop"] = item["time_stop"] + offset_time
                pass
        except Exception as e:
            logger.error(f"{e}")
            pass
        output_reports.append(item)

    op_dict = dict()
    op_dict["reports"] = output_reports

    return op_dict


def set_protocol_no_answer(gt_dict):

    logger.info("Setting all Protocol fields to no_answer")
    output_reports = list()
    for item in gt_dict["reports"]:
        try:
            if item["report_type"] == "signal":
                item["protocol"] = "no_answer"
            elif item["report_type"] == "energy":
                pass
        except Exception as e:
            logger.error(f"{e}")
            pass
        output_reports.append(item)

    op_dict = dict()
    op_dict["reports"] = output_reports

    return op_dict



def transpose_num_letter(s):
    # Use a regular expression to check if the string follows the format
    match = re.match(r'([a-z]+)(\d+)', s)
    if match:
        letters = match.group(1)
        numbers = match.group(2)
        # Convert the string to the desired format
        return numbers + "_" + letters
    else:
        return None

def modulation_lookup(modulation_input: str = None):
    
    transposed_string = transpose_num_letter(modulation_input)    
    if not modulation_input:
        return "no_answer"
    elif transposed_string:
        return transposed_string
    elif modulation_input == "fm" or modulation_input == "am":
        return f"{modulation_input}_analog"
    elif modulation_input == "ssb" or modulation_input == "fh"  or modulation_input == "ofdm":
        return "no_answer"
    else:
        return modulation_input
    
def translate_modulation(gt_dict):
    
    logger.info("Attempting to translate modulation field to score-able format")
    output_reports = list()
    
    for item in gt_dict["reports"]:
        try:
            if item["report_type"] == "signal":
                item["modulation"] = modulation_lookup(item["modulation"])
            elif item["report_type"] == "energy":
                pass
        except Exception as e:
            logger.error(f"{e}")
            pass
        output_reports.append(item)
    
    op_dict = dict()
    op_dict["reports"] = output_reports
    
    return op_dict


def set_modulation_no_answer(gt_dict):

    logger.info("Setting all Modulation fields to no_answer")
    output_reports = list()
    for item in gt_dict["reports"]:
        try:
            if item["report_type"] == "signal":
                item["modulation"] = "no_answer"
            elif item["report_type"] == "energy":
                pass
        except Exception as e:
            logger.error(f"{e}")
            pass
        output_reports.append(item)

    op_dict = dict()
    op_dict["reports"] = output_reports

    return op_dict


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION]", description="Offset report and store in file"
    )
    parser.add_argument(
        "time",
        type=float,
        default=None,
        help="POSIX timestamp to offset",
    )
    parser.add_argument(
        "report",
        type=str,
        default=None,
        help="Report file to offset",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{parser.prog} version " + __version__,
    )

    return parser


def main():
    
    parser = init_argparse()
    args = parser.parse_args()
    
    logger.info(f"Offsetting report: {args.report} by {args.time} seconds")
    try:
        offset_dict = offset_ground_truth(args.report, args.time)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    
    output_report = ".".join(args.report.split(".")[:-1]) + "_offset.json"
    
    logging.info(f"Saving offset to {output_report}")
    # Dump gt
    with open(output_report, "w") as outfile:
        json.dump(offset_dict, outfile, indent=4)
    


if __name__ == "__main__":
    main()


