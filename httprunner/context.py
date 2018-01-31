# -*- coding: utf-8 -*-
import copy
import os
import re
import sys
from collections import OrderedDict

from httprunner import utils
from httprunner.testcase import TestcaseParser


class Context(object):
    """ Manages context functions and variables.
        context has two levels, testset and testcase.
    """
    def __init__(self):
        #OrderedDict：有序字典
        self.testset_shared_variables_mapping = OrderedDict()
        self.testcase_variables_mapping = OrderedDict()
        self.testcase_parser = TestcaseParser()
        #初始化context，
        self.init_context()

    def init_context(self, level='testset'):
        """
        testset level context initializes when a file is loaded,
        testcase level context initializes when each testcase starts.
        """
        if level == "testset":
            self.testset_functions_config = {}
            self.testset_request_config = {}
            self.testset_shared_variables_mapping = OrderedDict()

        # testcase config shall inherit from testset configs,
        # but can not change testset configs, that's why we use copy.deepcopy here.
        self.testcase_functions_config = copy.deepcopy(self.testset_functions_config)
        self.testcase_variables_mapping = copy.deepcopy(self.testset_shared_variables_mapping)
        #更新实例testcase_parser的变量functions的值
        self.testcase_parser.bind_functions(self.testcase_functions_config)
        # 更新实例testcase_parser的变量variables的值
        self.testcase_parser.update_binded_variables(self.testcase_variables_mapping)

        if level == "testset":
            self.import_module_items(["httprunner.built_in"], "testset")

    def config_context(self, config_dict, level):
        #如果level是testset，将实例testcase_parser的变量file_path的值更新为config_dict里path的值
        if level == "testset":
            self.testcase_parser.file_path = config_dict.get("path", None)
        #导入config_dict里的模块
        requires = config_dict.get('requires', [])
        self.import_requires(requires)

        function_binds = config_dict.get('function_binds', {})
        self.bind_functions(function_binds, level)

        # import_module_functions will be deprecated soon
        module_items = config_dict.get('import_module_items', []) \
            or config_dict.get('import_module_functions', [])
        self.import_module_items(module_items, level)

        variables = config_dict.get('variables') \
            or config_dict.get('variable_binds', OrderedDict())
        self.bind_variables(variables, level)

    def import_requires(self, modules):
        """ import required modules dynamically
        """
        for module_name in modules:
            globals()[module_name] = utils.get_imported_module(module_name)

    def bind_functions(self, function_binds, level="testcase"):
        """ Bind named functions within the context
            This allows for passing in self-defined functions in testing.
            e.g. function_binds:
            {
                "add_one": lambda x: x + 1,             # lambda function
                "add_two_nums": "lambda x, y: x + y"    # lambda function in string
            }
        """
        eval_function_binds = {}
        for func_name, function in function_binds.items():
            if isinstance(function, str):
                function = eval(function)
            eval_function_binds[func_name] = function

        self.__update_context_functions_config(level, eval_function_binds)

    def import_module_items(self, modules, level="testcase"):
        """ import modules and bind all functions within the context
        """
        #在程序的生命周期内引入工作目录路径到环境变量
        sys.path.insert(0, os.getcwd())
        for module_name in modules:
            #导入并返回指定的模块
            imported_module = utils.get_imported_module(module_name)
            #将导入的模块里，类型是function的筛选出来，存入字典imported_functions_dict中
            imported_functions_dict = utils.filter_module(imported_module, "function")
            #将imported_functions_dict字典更新到列表testcase_functions_config
            #和实例testcase_parser的列表bind_functions
            self.__update_context_functions_config(level, imported_functions_dict)
            # 将导入的模块里，类型是variable的筛选出来，存入字典imported_variables_dict中
            imported_variables_dict = utils.filter_module(imported_module, "variable")

            self.bind_variables(imported_variables_dict, level)

    def bind_variables(self, variables, level="testcase"):
        """ bind variables to testset context or current testcase context.
            variables in testset context can be used in all testcases of current test suite.

        @param (list or OrderDict) variables, variable can be value or custom function.
            if value is function, it will be called and bind result to variable.
        e.g.
            OrderDict({
                "TOKEN": "debugtalk",
                "random": "${gen_random_string(5)}",
                "json": {'name': 'user', 'password': '123456'},
                "md5": "${gen_md5($TOKEN, $json, $random)}"
            })
        """
        #如果variables是列表，将其转换为有序字典
        if isinstance(variables, list):
            variables = utils.convert_to_order_dict(variables)
        #循环处理variables的值，将带有表达式或引用等需要处理的值处理为正常的值
        for variable_name, value in variables.items():
            variable_evale_value = self.testcase_parser.parse_content_with_bindings(value)

            if level == "testset":
                self.testset_shared_variables_mapping[variable_name] = variable_evale_value

            self.testcase_variables_mapping[variable_name] = variable_evale_value
            self.testcase_parser.update_binded_variables(self.testcase_variables_mapping)

    def bind_extracted_variables(self, variables):
        """ bind extracted variables to testset context
        @param (OrderDict) variables
            extracted value do not need to evaluate.
        """
        for variable_name, value in variables.items():
            self.testset_shared_variables_mapping[variable_name] = value
            self.testcase_variables_mapping[variable_name] = value
            self.testcase_parser.update_binded_variables(self.testcase_variables_mapping)

    def __update_context_functions_config(self, level, config_mapping):
        """
        @param level: testset or testcase
        @param config_type: functions
        @param config_mapping: functions config mapping
        """
        # 如果level是"testset",将导入模块中的function字典更新到列表testset_functions_config
        if level == "testset":
            self.testset_functions_config.update(config_mapping)
        #将导入模块中的function字典更新到列表testcase_functions_config
        self.testcase_functions_config.update(config_mapping)
        #将导入模块中的function字典更新到类TestcaseParser的实例testcase_parser，的列表bind_functions
        self.testcase_parser.bind_functions(self.testcase_functions_config)

    def get_parsed_request(self, request_dict, level="testcase"):
        """ get parsed request with bind variables and functions.
        @param request_dict: request config mapping
        @param level: testset or testcase
        """
        if level == "testset":
            #将非常规类型的参数处理为常规类型的参数，以字典形式返回
            request_dict = self.testcase_parser.parse_content_with_bindings(
                request_dict
            )
            #将处理后的参数字典更新到testset_request_config{}
            self.testset_request_config.update(request_dict)
        #合并字典
        testcase_request_config = utils.deep_update_dict(
            copy.deepcopy(self.testset_request_config),
            request_dict
        )
        parsed_request = self.testcase_parser.parse_content_with_bindings(
            testcase_request_config
        )

        return parsed_request

    def get_testcase_variables_mapping(self):
        return self.testcase_variables_mapping

    def exec_content_functions(self, content):
        """ execute functions in content.
        """
        self.testcase_parser.eval_content_functions(content)
