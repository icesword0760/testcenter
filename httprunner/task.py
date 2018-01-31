# -*- coding: utf-8 -*-
import logging
import unittest

from httprunner import exception, runner, testcase, utils


class ApiTestCase(unittest.TestCase):
    """ create a testcase.
    """
    def __init__(self, test_runner, testcase_dict):
        super(ApiTestCase, self).__init__()
        self.test_runner = test_runner
        self.testcase_dict = testcase_dict

    def runTest(self):
        """ run testcase and check result.
        """
        self.assertTrue(self.test_runner._run_test(self.testcase_dict))

class ApiTestSuite(unittest.TestSuite):
    """ create test suite with a testset, it may include one or several testcases.
        each suite should initialize a separate Runner() with testset config.
    """
    def __init__(self, testset):
        super(ApiTestSuite, self).__init__()
        #生成一个Runner的实例：test_runner，Runner包含了各种执行测试用例的方法
        self.test_runner = runner.Runner()
        #从testset里读取config信息，作为字典config_dict保存
        self.config_dict = testset.get("config", {})
        #执行Runner类的init_config方法，当level为testset时，处理config_dict里的值为常规参数类型并作为字典返回
        self.test_runner.init_config(self.config_dict, level="testset")
        testcases = testset.get("testcases", [])
        self._add_tests_to_suite(testcases)

    def _add_tests_to_suite(self, testcases):
       #testcases:每个文件里的测试用例列表list，循环得到每个case的name作为ApiTestCase.runTest方法的文档属性
        for testcase_dict in testcases:
            if utils.PYTHON_VERSION == 3:
                ApiTestCase.runTest.__doc__ = testcase_dict['name']
            else:
                ApiTestCase.runTest.__func__.__doc__ = testcase_dict['name']

            test = ApiTestCase(self.test_runner, testcase_dict)
            self.addTest(test)

    def print_output(self):
        output_variables_list = self.config_dict.get("output", [])
        self.test_runner.generate_output(output_variables_list)

class TaskSuite(unittest.TestSuite):
    """ create test task suite with specified testcase path.
        each task suite may include one or several test suite.
    """
    def __init__(self, testsets):
        super(TaskSuite, self).__init__()
        self.suite_list = []
        #testsets是一个load_testcases_by_path()方法解析yml文件返回的列表list，每个列表项是一个testset字典dict，每个testset包含了公共模块（api:{},config:{},name:str）
        #和一个testcase[]的list，每个testcase的list以字典形式保存用例需要的数据
        #testsets = testcase.load_testcases_by_path(testcase_path)
        testsets = testsets
        if not testsets:
            raise exception.TestcaseNotFound
        #循环得到的testsets列表，将每个testset用ApiTestSuite方法处理
        for testset in testsets:
            suite = ApiTestSuite(testset)
            self.addTest(suite)
            self.suite_list.append(suite)

    @property
    def tasks(self):
        return self.suite_list
