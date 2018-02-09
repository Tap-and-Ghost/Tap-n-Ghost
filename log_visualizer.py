#!/usr/bin/env python3
import os
import re
import csv
from datetime import datetime, timedelta
from itertools import takewhile, starmap
from functools import reduce
import numpy as np

UNLOCK_DETECTORS = {
    # for a smartphone that returns sel_res=60 when it is in unlocked state
    "A60": lambda t, a, b, f: "sel_res=60" in a,

    # for a smartphone that returns sel_res=60 when it is in unlocked/locked state.
    # we do not use such a smartphone for our analysis
    "A60'": lambda t, a, b, f: "sel_res=60" in a,

    # for a smartphone that returns sensf_res when it is in unlocked state
    "F": lambda t, a, b, f: "sensf_res" in f,

    # dummy. for a smartphone with HuaweiPay
    "HuaweiPay": lambda t, a, b, f: False,
}
TASK_SECS = 15 * 60
FREE_SECS = 10 * 60
NA_COLOR_VALUE = 0.3


def normalize(rows, time_range, unlock_detector):
    def is_attackable(rows_at_t): return any(starmap(unlock_detector, rows_at_t))

    normalized_array = []
    rows_temp = rows[len(list(takewhile(lambda r: r[0] < time_range[0], rows))):]
    for t in time_range:
        rows_at_t = list(takewhile(lambda r: r[0] == t, rows_temp))
        rows_temp = rows_temp[len(rows_at_t):]

        normalized_array.append(
            normalized_array[-1] if len(rows_at_t) == 0 and normalized_array
            else is_attackable(rows_at_t)
        )
    return normalized_array


def gen_time_range(min_time, max_time):
    time_range = []
    time = min_time
    while True:
        if time > max_time:
            break
        time_range.append(time.strftime("%H:%M:%S"))
        time += timedelta(seconds=1)
    return time_range


def process_single_experiment(log_file_dir, task_start_time_str, task_end_time_str, nfc_type, *option):
    if nfc_type == "A60'":  # As mentioned above, we do not use A60' results to generate the figure in the paper
        return (None, None)

    log_paths = [os.path.join(log_file_dir, fp) for fp in os.listdir(log_file_dir)
                 if os.path.isfile(os.path.join(log_file_dir, fp)) and fp.endswith(".csv")]
    assert len(log_paths) == 16, "16 logfiles, from Alpha to Papa, are required"

    log_data = {}
    for log_path in log_paths:
        f = open(log_path, "r")
        rows = list(csv.reader(f))
        log_data[os.path.basename(log_path).replace(".csv", "")] = rows

    log_min_time = min(map(lambda a: datetime.strptime(a[0][0], "%H:%M:%S"), log_data.values()))
    log_max_time = max(map(lambda a: datetime.strptime(a[-1][0], "%H:%M:%S"), log_data.values()))

    min_time = datetime.strptime(task_start_time_str, "%H:%M:%S")
    max_time = log_max_time
    switch_time = datetime.strptime(task_end_time_str, "%H:%M:%S")

    if "modify_task_start_time" in option:
        min_time = log_min_time
    assert log_min_time <= min_time < switch_time < log_max_time, \
        f"log start time ({log_min_time}) <= task start time ({min_time}) < task end time ({switch_time}) < log end time ({log_max_time})"
    assert (log_max_time - switch_time).total_seconds() > FREE_SECS, f"free time must be longer than 10 min."

    time_range = gen_time_range(min_time, max_time)
    switch_time_idx = int((switch_time - min_time).total_seconds())

    unlock_detector = UNLOCK_DETECTORS[nfc_type]
    normalized_result = reduce(
        np.logical_or,
        [np.array(normalize(rows, time_range, unlock_detector)) for rows in log_data.values()]
    )
    task_result, free_result = \
        normalized_result[:switch_time_idx][:TASK_SECS], normalized_result[switch_time_idx + 1:][:FREE_SECS]

    # append N/A value if a participant finishes the task less than 15 min.
    task_result = np.append(task_result, np.full((TASK_SECS - len(task_result)), NA_COLOR_VALUE))

    if "nfc_off_free" in option:
        free_result = np.full((FREE_SECS,), NA_COLOR_VALUE)
    if "pay_nfc" in option:
        task_result = np.full((TASK_SECS,), NA_COLOR_VALUE)
        free_result = np.full((FREE_SECS,), NA_COLOR_VALUE)

    def result_printer(result):
        attackable_len = len(list(filter(lambda x: x == 1, result)))
        all_len = len(list(result))
        print(f"{attackable_len:>3}/{all_len} ({attackable_len/all_len*100:>4.3}%, {all_len/60:.3} min)\t", end="")
    result_printer(task_result)
    result_printer(free_result)
    print()

    return(task_result, free_result)


def plot_results(results):
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    def plot_result(ax, result_1d):
        ax.pcolormesh(result_1d[np.newaxis, :], cmap="binary", norm=matplotlib.colors.Normalize(0, 1))
        ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=60))
        ax.xaxis.set_major_formatter(matplotlib.ticker.NullFormatter())
        ax.tick_params(axis='y', left=False, labelleft=False)

    fig = plt.figure(figsize=(8, 6))
    fig.subplots_adjust(bottom=0.18)  # for legend space
    gs = gridspec.GridSpec(len(results), 2, width_ratios=[TASK_SECS, FREE_SECS])

    results = filter(lambda r: r[0] is not None, results)  # filter out A60' results
    for i, (task_res, free_res) in enumerate(results):
        if task_res is None and free_res is None:  # skip filtered out results (or A60' results)
            continue
        ax_t = plt.subplot(gs[i, 0])
        ax_t.set_ylabel('P' + str(i + 1), fontdict={'family': 'monospace'},
                        rotation='horizontal', horizontalalignment='right', verticalalignment='center')
        ax_t.yaxis.set_label_coords(-0.020, 0.5)
        plot_result(ax_t, task_res)

        ax_f = plt.subplot(gs[i, 1])
        plot_result(ax_f, free_res)

    # draw x labels
    ax_t.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: str(int(x / 60))))
    ax_f.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: str(int(x / 60))))
    ax_t.set_xlabel("Task Time [min]")
    ax_f.set_xlabel("Free Time [min]")

    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor='black', edgecolor='black', label='Attackable'),
        Patch(facecolor='white', edgecolor='black', label='Not Attackable'),
        Patch(facecolor=[0.7] * 3, edgecolor='black', label='Not Available')
    ]
    plt.legend(handles=legend_handles, bbox_to_anchor=(-0.3, -5.0), loc='lower center', ncol=3)

    # plt.show()
    plt.savefig("userstudy_result.pdf", bbox_inches="tight", pad_inches=0.0)


if __name__ == '__main__':
    regex_log_dir_name = re.compile("^[0-9]{14}_[0-9]{2}$")
    dir_list = sorted(filter(regex_log_dir_name.match, os.listdir()))

    with open("config.txt", "r") as f:
        config_lines = f.readlines()
    assert len(dir_list) == len(config_lines)

    results = []
    for d, l in zip(dir_list, config_lines):
        result = process_single_experiment(d, *l.split())
        results.append(result)
    plot_results(results)
