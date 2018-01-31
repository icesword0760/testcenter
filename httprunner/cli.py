# -*- coding: utf-8 -*-
import argparse
import logging
import os
import sys
import unittest
from collections import OrderedDict

from pyunitreport import __version__ as pyu_version
from pyunitreport import HTMLTestRunner

from httprunner import __version__ as ate_version
from httprunner import exception
from httprunner.task import TaskSuite
from httprunner.utils import create_scaffold
import time

def main_ate(testsets):
    """ API test: parse command line options and run commands.
    """
    #解析测试用例的路径，并用TaskSuite方法生成testsuite
    task_suite = TaskSuite(testsets)
    output_folder_name = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))+" Task Result Report"
    kwargs = {
        "output": output_folder_name,
        "report_name": "name",
        "failfast": False
    }
    results = {}
    success = True
    result = HTMLTestRunner(**kwargs).run(task_suite)
    results[output_folder_name] = OrderedDict({
        "total": result.testsRun,
        "successes": len(result.successes),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped)
    })

    if len(result.successes) != result.testsRun:
        success = False

    for task in task_suite.tasks:
        task.print_output()
    #runner = unittest.TextTestRunner()


def main_locust():
    """ Performance test with locust: parse command line options and run commands.
    """
    try:
        from httprunner import locusts
    except ImportError:
        msg = "Locust is not installed, install first and try again.\n"
        msg += "install command: pip install locustio"
        print(msg)
        exit(1)

    sys.argv[0] = 'locust'
    if len(sys.argv) == 1:
        sys.argv.extend(["-h"])

    if sys.argv[1] in ["-h", "--help", "-V", "--version"]:
        locusts.main()
        sys.exit(0)

    try:
        testcase_index = sys.argv.index('-f') + 1
        assert testcase_index < len(sys.argv)
    except (ValueError, AssertionError):
        print("Testcase file is not specified, exit.")
        sys.exit(1)

    testcase_file_path = sys.argv[testcase_index]
    sys.argv[testcase_index] = locusts.parse_locustfile(testcase_file_path)

    if "--full-speed" in sys.argv:
        locusts.run_locusts_at_full_speed(sys.argv)
    else:
        locusts.main()
