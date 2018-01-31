# -*- coding: utf-8 -*-
import ast
import codecs
import json
import logging
import os
import re

import yaml
from httprunner import exception, utils

variable_regexp = r"\$([\w_]+)"
function_regexp = r"\$\{([\w_]+\([\$\w_ =,]*\))\}"
function_regexp_compile = re.compile(r"^([\w_]+)\(([\$\w_ =,]*)\)$")
test_def_overall_dict = {
    "loaded": False,
    "api": {},
    "suite": {}
}
testcases_cache_mapping = {}


def _load_yaml_file(yaml_file):
    """ load yaml file and check file content format
    """
    with codecs.open(yaml_file, 'r+', encoding='utf-8') as stream:
        yaml_content = yaml.load(stream)
        check_format(yaml_file, yaml_content)
        return yaml_content

def _load_json_file(json_file):
    """ load json file and check file content format
    """
    with codecs.open(json_file, encoding='utf-8') as data_file:
        try:
            json_content = json.load(data_file)
        except exception.JSONDecodeError:
            err_msg = u"JSONDecodeError: JSON file format error: {}".format(json_file)
            logging.error(err_msg)
            raise exception.FileFormatError(err_msg)

        check_format(json_file, json_content)
        return json_content

def _load_file(testcase_file_path):
    file_suffix = os.path.splitext(testcase_file_path)[1]
    if file_suffix == '.json':
        return _load_json_file(testcase_file_path)
    elif file_suffix in ['.yaml', '.yml']:
        return _load_yaml_file(testcase_file_path)
    else:
        # '' or other suffix
        err_msg = u"file is not in YAML/JSON format: {}".format(testcase_file_path)
        logging.warning(err_msg)
        return []

def extract_variables(content):
    """ extract all variable names from content, which is in format $variable
    @param (str) content
    @return (list) variable name list

    e.g. $variable => ["variable"]
         /blog/$postid => ["postid"]
         /$var1/$var2 => ["var1", "var2"]
         abc => []
    """
    # 按照规定的正则表达式处理字符串并以列表形式返回
    try:
        return re.findall(variable_regexp, content)
    except TypeError:
        return []

def extract_functions(content):
    """ extract all functions from string content, which are in format ${fun()}
    @param (str) content
    @return (list) functions list

    e.g. ${func(5)} => ["func(5)"]
         ${func(a=1, b=2)} => ["func(a=1, b=2)"]
         /api/1000?_t=${get_timestamp()} => ["get_timestamp()"]
         /api/${add(1, 2)} => ["add(1, 2)"]
         "/api/${add(1, 2)}?_t=${get_timestamp()}" => ["add(1, 2)", "get_timestamp()"]
    """
    #按照规定的正则表达式处理字符串并以列表形式返回
    try:
        return re.findall(function_regexp, content)
    except TypeError:
        return []

def parse_string_value(str_value):
    """ parse string to number if possible
    e.g. "123" => 123
         "12.2" => 12.3
         "abc" => "abc"
         "$var" => "$var"
    """
    try:
        return ast.literal_eval(str_value)
    except ValueError:
        return str_value
    except SyntaxError:
        # e.g. $var, ${func}
        return str_value

def parse_function(content):
    """ parse function name and args from string content.
    @param (str) content
    @return (dict) function name and args

    e.g. func() => {'func_name': 'func', 'args': [], 'kwargs': {}}
         func(5) => {'func_name': 'func', 'args': [5], 'kwargs': {}}
         func(1, 2) => {'func_name': 'func', 'args': [1, 2], 'kwargs': {}}
         func(a=1, b=2) => {'func_name': 'func', 'args': [], 'kwargs': {'a': 1, 'b': 2}}
         func(1, 2, a=3, b=4) => {'func_name': 'func', 'args': [1, 2], 'kwargs': {'a':3, 'b':4}}
    """
    function_meta = {
        "args": [],
        "kwargs": {}
    }
    #按照规定的正则表达式解析content
    matched = function_regexp_compile.match(content)
    #将正则匹配结果的第一部分的值给function_meta["func_name"]
    function_meta["func_name"] = matched.group(1)
    #去掉参数args里的空格，如果args为空则直接返回function_meta
    args_str = matched.group(2).replace(" ", "")
    if args_str == "":
        return function_meta
    #按逗号,分割args并将结果作为list赋值给args_list
    args_list = args_str.split(',')
    #循环处理列表args_list的值，如果arg含有"="，则按"="分割，并将其作为字典存入function_meta["kwargs"]
    #否则作为列表list存入function_meta["args"]
    for arg in args_list:
        if '=' in arg:
            key, value = arg.split('=')
            function_meta["kwargs"][key] = parse_string_value(value)
        else:
            function_meta["args"].append(parse_string_value(arg))

    return function_meta

def load_test_dependencies():
    """ load all api and suite definitions.
        default api folder is "$CWD/tests/api/".
        default suite folder is "$CWD/tests/suite/".
    """
    test_def_overall_dict["loaded"] = True
    test_def_overall_dict["api"] = {}
    test_def_overall_dict["suite"] = {}

    # load api definitions
    #传入默认路径$CWD/tests/api/，调用load_folder_files方法，递归解析路径，将默认路径下所有yml文件的路径作为列表list赋值给api_files
    api_def_folder = os.path.join(os.getcwd(), "tests", "api")
    api_files = utils.load_folder_files(api_def_folder)

    for test_file in api_files:
        testset = load_test_file(test_file)
        test_def_overall_dict["api"].update(testset["api"])

    # load suite definitions
    # 传入默认路径$CWD/tests/suite/，调用load_folder_files方法，递归解析路径，将默认路径下所有yml文件的路径作为列表list赋值给suite_files
    suite_def_folder = os.path.join(os.getcwd(), "tests", "suite")
    suite_files = utils.load_folder_files(suite_def_folder)

    for suite_file in suite_files:
        suite = load_test_file(suite_file)
        if "def" not in suite["config"]:
            raise exception.ParamsError("def missed in suite file: {}!".format(suite_file))

        call_func = suite["config"]["def"]
        function_meta = parse_function(call_func)
        suite["function_meta"] = function_meta
        test_def_overall_dict["suite"][function_meta["func_name"]] = suite

def load_testcases_by_path(path):
    """ load testcases from file path
    @param path: path could be in several type
        - absolute/relative file path
        - absolute/relative folder path
        - list/set container with file(s) and/or folder(s)
    @return testcase sets list, each testset is corresponding to a file
        [
            testset_dict_1,
            testset_dict_2
        ]
    """
    #判断传入的路径是否是列表list或者集合set类型，如果是，则递归解析路径path，并将解析结果放入列表testsets[]
    if isinstance(path, (list, set)):
        testsets = []

        for file_path in set(path):
            testset = load_testcases_by_path(file_path)
            if not testset:
                continue
            testsets.extend(testset)

        return testsets
    #判断是否是绝对路径，如果不是，用当前工作目录的路径加上path作为新的路径
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    #如果路径已经被记录在字典testcases_cache_mapping里，直接返回
    if path in testcases_cache_mapping:
        return testcases_cache_mapping[path]
    #判断路径是否是文件夹类型，如果是，返回该文件夹下所有测试用例文件的路径files_list，再将其递归解析
    if os.path.isdir(path):
        files_list = utils.load_folder_files(path)
        testcases_list = load_testcases_by_path(files_list)
    #判断路径是否是文件类型，如果是，调用load_test_file对path进行解析
    elif os.path.isfile(path):
        try:
            testset = load_test_file(path)
            #如果testset的testcase或者api字段有值的话，将该testset加入列表testcases_list
            #testset是字典dict格式的对象，结构为{"name": "desc1","config": {},"api": {},"testcases": [testcase11, testcase12] }
            if testset["testcases"] or testset["api"]:
                testcases_list = [testset]
            else:
                testcases_list = []
        except exception.FileFormatError:
            testcases_list = []
    #如果既不是目录也不是文件，输出报错日志，同时置testcases_list为空值
    else:
        logging.error(u"file not found: {}".format(path))
        testcases_list = []
    #testcases_cache_mapping是一个字典dict，记录了测试文件.yml的路径和其解析出来的testset的对应关系
    testcases_cache_mapping[path] = testcases_list
    return testcases_list

def load_test_file(file_path):
    """ load testset file, get testset data structure.
    @param file_path: absolute valid testset file path
    @return testset dict
        {
            "name": "desc1",
            "config": {},
            "api": {},
            "testcases": [testcase11, testcase12]
        }
    """
    testset = {
        "name": "",
        "config": {
            "path": file_path
        },
        "api": {},
        "testcases": []
    }
    tests_list = _load_file(file_path)

    for item in tests_list:
        for key in item:
            if key == "config":
                testset["config"].update(item["config"])
                testset["name"] = item["config"].get("name", "")

            elif key == "test":
                test_block_dict = item["test"]
                if "api" in test_block_dict:
                    ref_name = test_block_dict["api"]
                    test_info = get_testinfo_by_reference(ref_name, "api")
                    test_block_dict.update(test_info)
                    testset["testcases"].append(test_block_dict)
                elif "suite" in test_block_dict:
                    ref_name = test_block_dict["suite"]
                    test_info = get_testinfo_by_reference(ref_name, "suite")
                    testset["testcases"].extend(test_info["testcases"])
                else:
                    testset["testcases"].append(test_block_dict)

            elif key == "api":
                api_def = item["api"].pop("def")
                function_meta = parse_function(api_def)
                func_name = function_meta["func_name"]

                api_info = {}
                api_info["function_meta"] = function_meta
                api_info.update(item["api"])
                testset["api"][func_name] = api_info

    return testset

def get_testinfo_by_reference(ref_name, ref_type):
    """ get test content by reference name
    @params:
        ref_name: reference name, e.g. api_v1_Account_Login_POST($UserName, $Password)
        ref_type: "api" or "suite"
    """
    function_meta = parse_function(ref_name)
    func_name = function_meta["func_name"]
    call_args = function_meta["args"]
    test_info = get_test_definition(func_name, ref_type)
    def_args = test_info.get("function_meta").get("args", [])

    if len(call_args) != len(def_args):
        raise exception.ParamsError("call args mismatch defined args!")

    args_mapping = {}
    for index, item in enumerate(def_args):
        if call_args[index] == item:
            continue

        args_mapping[item] = call_args[index]

    if args_mapping:
        test_info = substitute_variables_with_mapping(test_info, args_mapping)

    return test_info

def get_test_definition(name, ref_type):
    """ get expected api or suite.
    @params:
        name: api or suite name
        ref_type: "api" or "suite"
    @return
        expected api info if found, otherwise raise ApiNotFound exception
    """
    if not test_def_overall_dict.get("loaded", False):
        load_test_dependencies()

    test_info = test_def_overall_dict.get(ref_type, {}).get(name)
    if not test_info:
        err_msg = "{} {} not found!".format(ref_type, name)
        if ref_type == "api":
            raise exception.ApiNotFound(err_msg)
        elif ref_type == "suite":
            raise exception.SuiteNotFound(err_msg)
        else:
            raise exception.ParamsError("ref_type can only be api or suite!")

    return test_info

def substitute_variables_with_mapping(content, mapping):
    """ substitute variables in content with mapping
    e.g.
    @params
        content = {
            'request': {
                'url': '/api/users/$uid',
                'headers': {'token': '$token'}
            }
        }
        mapping = {"$uid": 1000}
    @return
        {
            'request': {
                'url': '/api/users/1000',
                'headers': {'token': '$token'}
            }
        }
    """
    if isinstance(content, bool):
        return content

    if isinstance(content, (int, utils.long_type, float, complex)):
        return content

    if not content:
        return content

    if isinstance(content, (list, set, tuple)):
        return [
            substitute_variables_with_mapping(item, mapping)
            for item in content
        ]

    if isinstance(content, dict):
        substituted_data = {}
        for key, value in content.items():
            eval_key = substitute_variables_with_mapping(key, mapping)
            eval_value = substitute_variables_with_mapping(value, mapping)
            substituted_data[eval_key] = eval_value

        return substituted_data

    # content is in string format here
    for var, value in mapping.items():
        if content == var:
            # content is a variable
            content = value
        else:
            content = content.replace(var, str(value))

    return content

def check_format(file_path, content):
    """ check testcase format if valid
    """
    if not content:
        # testcase file content is empty
        err_msg = u"Testcase file content is empty: {}".format(file_path)
        logging.error(err_msg)
        raise exception.FileFormatError(err_msg)

    elif not isinstance(content, (list, dict)):
        # testcase file content does not match testcase format
        err_msg = u"Testcase file content format invalid: {}".format(file_path)
        logging.error(err_msg)
        raise exception.FileFormatError(err_msg)


class TestcaseParser(object):

    def __init__(self, variables={}, functions={}, file_path=None):
        #更新variables的值为{}
        self.update_binded_variables(variables)
        #更新functions的值为{}
        self.bind_functions(functions)
        # 更新file_path的值为None
        self.file_path = file_path

    def update_binded_variables(self, variables):
        """ bind variables to current testcase parser
        @param (dict) variables, variables binds mapping
            {
                "authorization": "a83de0ff8d2e896dbd8efb81ba14e17d",
                "random": "A2dEx",
                "data": {"name": "user", "password": "123456"},
                "uuid": 1000
            }
        """
        self.variables = variables

    def bind_functions(self, functions):
        """ bind functions to current testcase parser
        @param (dict) functions, functions binds mapping
            {
                "add_two_nums": lambda a, b=1: a + b
            }
        """
        self.functions = functions

    def get_bind_item(self, item_type, item_name):
        #如果item_type是function，且item_name（也就是传来的方法名function_name）存在于字典functions中，直接返回该方法
        if item_type == "function":
            if item_name in self.functions:
                return self.functions[item_name]
        # 如果item_type是variable，且item_name存在于有序字典variables中，直接返回该变量
        elif item_type == "variable":
            if item_name in self.variables:
                return self.variables[item_name]
        else:
            raise exception.ParamsError("bind item should only be function or variable.")

        try:
            assert self.file_path is not None
            return utils.search_conf_item(self.file_path, item_type, item_name)
        except (AssertionError, exception.FunctionNotFound):
            raise exception.ParamsError(
                "{} is not defined in bind {}s!".format(item_name, item_type))

    def eval_content_functions(self, content):
        #按规定的正则表达式处理字符串content，并将结果以列表形式赋值给functions_list
        functions_list = extract_functions(content)
        for func_content in functions_list:
            #处理func_content，返回function_meta，function_meta是一个形式为{'func_name': 'func', 'args': [], 'kwargs': {}}的字典
            function_meta = parse_function(func_content)
            #从function_meta中抽取方法名
            func_name = function_meta['func_name']
            #调用get_bind_item得到方法提取的方法名对应的方法
            func = self.get_bind_item("function", func_name)
            #从function_meta抽取args([])类型的参数
            args = function_meta.get('args', [])
            # 从function_meta抽取kwargs({})类型的参数
            kwargs = function_meta.get('kwargs', {})
            #调用parse_content_with_bindings递归解析参数args
            args = self.parse_content_with_bindings(args)
            #调用parse_content_with_bindings递归解析参数kwargs
            kwargs = self.parse_content_with_bindings(kwargs)
            #用获取的参数传参进获取的方法来执行
            eval_value = func(*args, **kwargs)

            func_content = "${" + func_content + "}"
            if func_content == content:
                # content is a variable
                content = eval_value
            else:
                # content contains one or many variables
                content = content.replace(
                    func_content,
                    str(eval_value), 1
                )

        return content

    def eval_content_variables(self, content):
        """ replace all variables of string content with mapping value.
        @param (str) content
        @return (str) parsed content

        e.g.
            variable_mapping = {
                "var_1": "abc",
                "var_2": "def"
            }
            $var_1 => "abc"
            $var_1#XYZ => "abc#XYZ"
            /$var_1/$var_2/var3 => "/abc/def/var3"
            ${func($var_1, $var_2, xyz)} => "${func(abc, def, xyz)}"
        """
        variables_list = extract_variables(content)
        for variable_name in variables_list:
            variable_value = self.get_bind_item("variable", variable_name)

            if "${}".format(variable_name) == content:
                # content is a variable
                content = variable_value
            else:
                # content contains one or many variables
                content = content.replace(
                    "${}".format(variable_name),
                    str(variable_value), 1
                )

        return content

    def parse_content_with_bindings(self, content):
        """ parse content recursively, each variable and function in content will be evaluated.

        @param (dict) content in any data structure
            {
                "url": "http://127.0.0.1:5000/api/users/$uid/${add_two_nums(1, 1)}",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "authorization": "$authorization",
                    "random": "$random",
                    "sum": "${add_two_nums(1, 2)}"
                },
                "body": "$data"
            }
        @return (dict) parsed content with evaluated bind values
            {
                "url": "http://127.0.0.1:5000/api/users/1000/2",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "authorization": "a83de0ff8d2e896dbd8efb81ba14e17d",
                    "random": "A2dEx",
                    "sum": 3
                },
                "body": {"name": "user", "password": "123456"}
            }
        """

        #如果content是个列表，则递归解析，返回一个解析后的列表list
        if isinstance(content, (list, tuple)):
            return [
                self.parse_content_with_bindings(item)
                for item in content
            ]
        # 如果content是个字典，则递归解析，返回一个解析后的列表dict
        if isinstance(content, dict):
            evaluated_data = {}
            for key, value in content.items():
                eval_key = self.parse_content_with_bindings(key)
                eval_value = self.parse_content_with_bindings(value)
                evaluated_data[eval_key] = eval_value

            return evaluated_data
        # 如果content是整型，则直接返回其值
        if isinstance(content, (int, utils.long_type, float, complex)):
            return content

        # content is in string format here
        #如果content是string类型且不为None，去掉首尾的空格重新赋值，否则置为空字符串
        content = "" if content is None else content.strip()

        # replace functions with evaluated value
        # Notice: eval_content_functions must be called before eval_content_variables
        content = self.eval_content_functions(content)

        # replace variables with binding value
        content = self.eval_content_variables(content)

        return content
