#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import signal
import sys
import os
import csv
from datetime import datetime
from mylib.sense_thread import SenseThread
from mylib.nfc_frontend_resolver import get_name_path_pairs

LOG_ROOT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "log")


def main():
    time_start = datetime.now()
    print('[*] Start Time: ' + str(time_start.now()))

    name_path_pairs = get_name_path_pairs()
    print("[*] " + str(len(name_path_pairs)) + " devices found")

    # make log dir
    if not os.path.exists(LOG_ROOT_DIR):
        os.makedirs(LOG_ROOT_DIR)
    log_dir = os.path.join(
        LOG_ROOT_DIR,
        "_".join([time_start.strftime("%Y%m%d%H%M%S")] + sys.argv[1:])
    )
    os.mkdir(log_dir)

    # open log files and start sense threads
    threads = []
    log_files = []
    for name, path in name_path_pairs:
        log_file_path = os.path.join(log_dir, name + ".csv")
        f = open(log_file_path, "w")
        log_writer = csv.writer(f)
        threads.append(SenseThread(name, path, log_writer, surpress=True))
        log_files.append(f)
    for th in threads:
        th.start()

    # wait Ctrl-C and stop all threads
    try:
        if threads:
            signal.pause()
    except (KeyboardInterrupt, SystemExit):
        print("[*] Now Interrupting. Don't press any key. Please wait...")
        for th in threads:
            th.stop()
        for th in threads:
            th.join()

    # close all log files
    for f in log_files:
        f.close()
    print('[*] Exit Time: ' + str(datetime.now()))


if __name__ == '__main__':
    main()
