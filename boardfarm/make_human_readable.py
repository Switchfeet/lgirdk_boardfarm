#!/usr/bin/env python

# Copyright (c) 2015
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.
"""make_human_readable : libraries to convert env and results in XML/JSON/HTML formats."""
import glob
import json
import logging
import os
import sys
import time
from collections import Counter
from string import Template

import boardfarm

owrt_tests_dir = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger("bft")


def pick_template_filename():
    """Decide which HTML file to use as template for results.

    This allows for different format for different audiences.
    """
    basic = owrt_tests_dir + "/html/template_results_basic.html"
    full = owrt_tests_dir + "/html/template_results.html"
    for modname in sorted(boardfarm.plugins):
        overlay = os.path.dirname(boardfarm.plugins[modname].__file__)
        tmp = glob.glob(
            os.path.join(overlay, "html", "template_results_basic.html")
        ) + glob.glob(os.path.join(overlay, "*", "html", "template_results_basic.html"))
        if len(tmp) > 0 and os.path.isfile(tmp[0]):
            basic = tmp[0]
            break
        tmp = glob.glob(
            os.path.join(overlay, "html", "template_results.html")
        ) + glob.glob(os.path.join(overlay, "*", "html", "template_results.html"))
        if len(tmp) > 0 and os.path.isfile(tmp[0]):
            full = tmp[0]
            break

    templates = {"basic": basic, "full": full}
    if os.environ.get("test_suite") == "daily_au":
        return templates["basic"]
    else:
        return templates["full"]


def build_station_info(board_info):
    """Build station information details."""
    ret = ""

    for device in board_info["devices"]:
        conn = device.get("conn_cmd", None)
        if not conn:
            conn = ":".join([device.get("ipaddr", ""), device.get("port", "")])
        ret += f"    <li>{device['name']} {device['type']} {conn}</li>\n"

    return ret


def xmlresults_to_html(
    test_results,
    output_name=owrt_tests_dir + "/results/results.html",
    title=None,
    board_info=None,
):
    """Parse XML result and convert to HTML."""

    if board_info is None:
        board_info = {}

    parameters = {
        "build_url": os.environ.get("BUILD_URL"),
        "total_test_time": "unknown",
        "summary_title": title,
        "board_type": "unknown",
        "location": "unknown",
        "report_time": "RUNNING or ABORTED",
    }
    try:
        parameters.update(board_info)
        parameters["misc"] = build_station_info(board_info)
    except Exception as e:
        logger.error(e)

    # categorize the results data
    results_table_lines = []
    results_fail_table_lines = []
    grade_counter = Counter()
    styles = {
        "OK": "ok",
        "Unexp OK": "uok",
        "SKIP": "skip",
        None: "skip",
        "FAIL": "fail",
        "Exp FAIL": "efail",
        "PENDING": "skip",
        "CC FAIL": "skip",
        "TD FAIL": "fail",
    }
    for i, t in enumerate(test_results):
        if t["grade"] is None:
            t["grade"] = "PENDING"
        t["num"] = i + 1
        t["style"] = styles[t["grade"]]
        if i % 2 == 0:
            t["row_style"] = "even"
        else:
            t["row_style"] = "odd"
        grade_counter[t["grade"]] += 1
        if "FAIL" == t["grade"]:
            results_fail_table_lines.append(
                '<tr class="%(row_style)s"><td>%(num)s</td><td class="%(style)s">%(grade)s</td><td>%(name)s</td></tr>'
                % t
            )
        results_table_lines.append(
            '<tr class="%(row_style)s"><td>%(num)s</td><td class="%(style)s">%(grade)s</td><td>%(name)s</td><td>%(message)s</td><td>%(elapsed_time).2fs</td></tr>'
            % t
        )
        if t["long_message"] != "":
            results_table_lines.append(
                f"<tr class=\"{t['row_style']}\"><td colspan=4><pre align=\"left\">"
            )
            results_table_lines.append(f"{t['long_message']}")
            results_table_lines.append("</pre></td></tr>")

    # process the summary counter
    results_summary_table_lines = []
    for e, v in grade_counter.items():
        results_summary_table_lines.append(
            '<tr><td class="%s">%s: %d</td></tr>' % (styles[e], e, v)
        )

    # Create the results tables
    parameters["table_results"] = "\n".join(results_table_lines)
    if len(results_fail_table_lines) == 0:
        parameters["table_fail_results"] = "<tr><td>None</td></tr>"
    else:
        parameters["table_fail_results"] = "\n".join(results_fail_table_lines)
    parameters["table_summary_results"] = "\n".join(results_summary_table_lines)

    # Other parameters
    try:
        test_seconds = int(os.environ.get("TEST_END_TIME")) - int(
            os.environ.get("TEST_START_TIME")
        )
        minutes = round((test_seconds / 60), 1)
        parameters["total_test_time"] = f"{minutes} minutes"
    except Exception as error:
        logger.error(error)

    # Report completion time
    try:
        end_timestamp = int(os.environ.get("TEST_END_TIME"))
        struct_time = time.localtime(end_timestamp)
        format_time = time.strftime("%Y-%m-%d %H:%M:%S", struct_time)
        parameters["report_time"] = f"{format_time}"
    except Exception as error:
        logger.error(error)

    # Substitute parameters into template html to create new html file
    template_filename = pick_template_filename()
    with open(template_filename) as fin, open(output_name, "w") as fout:
        f = fin.read()
        s = Template(f)
        fout.write(s.substitute(parameters))


def get_title():
    """Get title from the environment."""
    try:
        title = os.environ.get("summary_title")
        if title:
            return title
    except Exception as error:
        logger.error(error)
    try:
        return os.environ.get("JOB_NAME")
    except Exception as error:
        logger.error(error)
        return None


if __name__ == "__main__":
    try:
        list_results = json.load(open(sys.argv[1]))["test_results"]
        xmlresults_to_html(list_results, title="Test Results")
    except Exception as e:
        logger.error(e)
        logger.error("To use make_human_readable.py:")
        logger.error("./make_human_readable.py results/test_results.json")
