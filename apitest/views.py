# -*- coding: utf-8
from django.shortcuts import render
from django.forms.models import model_to_dict
from django.http import HttpResponse
from apitest.models import TestSuite, TestCase, TestProject
from httprunner.cli import main_ate
from django.db import transaction
from django.shortcuts import render_to_response
import json
import os
# Create your views here.
def run_suite(request):
    """
    根据传入的project_id查询出suiteid列表，循环读取处理生成testsets[],传入main_ate()执行测试并生成报告
    :param request: 传入的project_id
    :return:
    """
    suites = []
    if request.method == 'POST':
        project_data = eval(request.body)
        if 'projectId' in project_data:
            project_id = project_data['projectId']
            suites = list(TestSuite.objects.filter(project_id=project_id, is_del=0).values_list('suite_id',flat=True))
        else:
            suites = project_data['suiteIdList']
        testsets = []
        for suite_id in suites:
            testset = {}
            testcases = {'testcases':[]}
            config = {}
            # 查询testsuite，并将结果queryset赋值给suite
            suite = TestSuite.objects.get(suite_id=suite_id, is_del=0)
            # 将queryset结果转换为dict类型
            suite = model_to_dict(suite)
            # 删除键值对suite_id
            suite.pop('suite_id')
            suite.pop('is_del')
            suite.pop('project_id')
            # 循环处理查询结果，将为空值的键值对删除
            for k, v in suite.items():
                if v == ''or v is None:
                    suite.pop(k)
                else:
                    try:
                        suite[k] = eval(v)
                    except:
                        suite[k] = v
            config['config'] = suite
            # 查询模块id下所有的testcase，将结果集queryset赋值给cases
            cases = TestCase.objects.filter(suite_id=suite_id, is_del=0).values()
            # 循环处理每一个testcase，删除空的键值对，并且将字符串转为py对象
            for case in cases:
                case.pop('case_id')
                case.pop('is_del')
                case.pop('suite_id_id')
                for k, v in case.items():
                    if v == ''or v is None:
                        case.pop(k)
                    else:
                        try:
                            case[k] = eval(v)
                        except:
                            case[k] = v
                testcases['testcases'].append(case)
            testset.update(config)
            testset.update(testcases)
            testsets.append(testset)
    print (testsets)
    main_ate(testsets)
    return HttpResponse(request)

def add_suite(request):
    """
    增加一个模块
    :param request:
    :return: 成功返回creat ok
    """
    if request.method == 'POST':
        suite_data = parse_data_to_object(request.body)
        suite_name = suite_data['name']
        suite_vars = suite_data['variables']
        suite_req = suite_data['request']
        project_id = suite_data['project_id']
        try:
            with transaction.atomic():
                TestSuite.objects.create(name=suite_name, variables=suite_vars, request=suite_req, project_id_id=project_id)
        except Exception as e:
            print (e)
            return HttpResponse("SQL Error...")
        return HttpResponse("Creat ok!")
    else:
        return HttpResponse("Error")

def add_case(request):
    """
    增加一个用例
    :param request:
    :return: 成功返回creat ok
    """
    if request.method == 'POST':
        case_data = parse_data_to_object(request.body)
        case_name = case_data['name']
        case_validate = case_data['validate']
        case_extract = case_data['extract']
        case_vars = case_data['variables']
        case_req = case_data['request']
        suite_id = case_data['suite_id']
        try:
            with transaction.atomic():
                TestCase.objects.create(name=case_name, variables=case_vars, request=case_req, suite_id_id=suite_id, validate=case_validate, extract=case_extract)
        except Exception as e:
            print (e)
            return HttpResponse("SQL Error...")
        return HttpResponse("Creat ok!")
    else:
        return HttpResponse("Error")

def get_project_list(request):
    """
    获取测试项目列表
    :param request:
    :return: 项目列表的信息
    """
    project_list = []
    project_data = TestProject.objects.filter(is_del=0).values()
    for _ in project_data:
        project_list.append(_)
    return HttpResponse(json.dumps(project_list))

def add_project(request):
    """
    增加一个项目
    :param request:
    :return: 成功返回creat ok
    """
    if request.method == 'POST':
        project_data = eval(request.body)
        project_name = project_data['projectName']
        tester_name = project_data['testerName']
        try:
            with transaction.atomic():
                TestProject.objects.create(name=project_name, tester=tester_name)
        except Exception as e:
            print (e)
            return HttpResponse("SQL Error...")
        return HttpResponse("Creat ok!")
    else:
        return HttpResponse("Error")

def get_suite_list(request):
    """
    根据传入的project_id查询对应的suite_list
    :param request:
    :return: suite_list的信息
    """
    suite_list = []
    project_id = request.GET['projectId']
    suite_data = TestSuite.objects.filter(project_id=project_id, is_del=0).values()
    for _ in suite_data:
        suite_list.append(_)
    return HttpResponse(json.dumps(suite_list))

def get_suite_detail(request):
    """
    获取测试项目详情
    :param request:
    :return: 项目详情
    """
    suite_id = request.GET['suiteId']
    suite_detail = TestSuite.objects.get(suite_id=suite_id, is_del=0)
    suite_detail = model_to_dict(suite_detail)
    for k, v in suite_detail.items():
        try:
            suite_detail[k] = eval(v)
        except:
            suite_detail[k] = v
    return HttpResponse(json.dumps(suite_detail))

def get_case_detail(request):
    """
    获取测试用例详情
    :param request:
    :return: 用例详情
    """
    case_id = request.GET['caseId']
    case_detail = TestCase.objects.get(case_id=case_id, is_del=0)
    case_detail = model_to_dict(case_detail)
    case_detail = parse_data_to_object(case_detail)
    if 'data' in case_detail['request'] and isinstance(case_detail['request']['data'], (dict)):
        case_detail['request']['data'] = str(case_detail['request']['data'])
    if len(case_detail['validate'])> 0:
        for _ in case_detail['validate']:
            if isinstance(_['expect'], (dict)):
                _['expect'] = str(_['expect'])
    if len(case_detail['variables'])> 0:
        for _ in case_detail['variables']:
            for k, v in _.items():
                if isinstance(_[k], (dict)):
                    _[k] = str(v)
    return HttpResponse(json.dumps(case_detail))

def update_suite(request):
    """
    修改一个模块
    :param request:
    :return: 成功返回creat ok
    """
    if request.method == 'POST':
        suite_data = parse_data_to_object(request.body)
        suite_name = suite_data['name']
        suite_vars = suite_data['variables']
        suite_req = suite_data['request']
        suite_id = suite_data['suiteId']
        project_id = suite_data['project_id']
        try:
            with transaction.atomic():
                TestSuite.objects.filter(suite_id=suite_id).update(name=suite_name, variables=suite_vars, request=suite_req, project_id_id=project_id)
        except Exception as e:
            print (e)
            return HttpResponse("SQL Error...")
        return HttpResponse("Creat ok!")
    else:
        return HttpResponse("Error")

def update_case(request):
    """
    修改一个用例
    :param request:
    :return: 成功返回creat ok
    """
    if request.method == 'POST':
        case_data = parse_data_to_object(request.body)
        case_id = case_data['caseId']
        case_name = case_data['name']
        case_validate = case_data['validate']
        case_extract = case_data['extract']
        case_vars = case_data['variables']
        case_req = case_data['request']
        suite_id = case_data['suite_id']
        try:
            with transaction.atomic():
                TestCase.objects.filter(case_id=case_id).update(name=case_name, variables=case_vars, request=case_req, suite_id_id=suite_id, validate=case_validate, extract=case_extract)
        except Exception as e:
            print (e)
            return HttpResponse("SQL Error...")
        return HttpResponse("Creat ok!")
    else:
        return HttpResponse("Error")

def del_suite(request):
    """
    修改一个模块
    :param request:
    :return: 成功返回creat ok
    """
    if request.method == 'POST':
        suite_data = eval(request.body)
        #print suite_data
        suite_id = suite_data['suiteId']
        try:
            with transaction.atomic():
                TestSuite.objects.filter(suite_id=suite_id).update(is_del=1)
                TestCase.objects.filter(suite_id_id=suite_id).update(is_del=1)
        except Exception as e:
            print (e)
            return HttpResponse("SQL Error...")
        return HttpResponse("Del ok!")
    else:
        return HttpResponse("Error")

def del_case(request):
    """
    修改一个模块
    :param request:
    :return: 成功返回creat ok
    """
    if request.method == 'POST':
        case_data = eval(request.body)
        #print case_data
        case_id = case_data['caseId']
        try:
            with transaction.atomic():
                TestCase.objects.filter(case_id=case_id).update(is_del=1)
        except Exception as e:
            print (e)
            return HttpResponse("SQL Error...")
        return HttpResponse("Del ok!")
    else:
        return HttpResponse("Error")

def parse_data_to_object(data):
    """
    将入参解析为py对象
    :param data:目前对dict，str，list，unicode做了处理
    :return:py对象，如果无法解析直接返回原值
    """
    #print "come in"
    #print data
    if isinstance(data, (dict)):
        for k, v in data.items():
            data[k] = parse_data_to_object(v)
    elif isinstance(data, (str)):
        try:
            #print "elseif"
            #print data
            return parse_data_to_object(eval(data))
        except:
            #print "except"
            #print data
            return data
    elif isinstance(data, (unicode)):
        try:
            #print "elseif unicode"
            #print data
            return parse_data_to_object(eval(data.encode("utf-8")))
        except:
            #print "except"
            #print data
            return data
    elif isinstance(data, (list)):
        for _ in data:
            _ = parse_data_to_object(_)
        return data
    #print "put"
    #print data
    return data

def get_report(request):
    report_name = request.GET['reportName']
    return render(request, report_name+"/name.html")

def get_reports_list(request):
    split_report_list = []
    reports_list = os.listdir("./reports")[::-1]
    for i in range(0, len(reports_list), 10):
        split_report_list.append(reports_list[i:i+10])
    index = int(request.GET['index'])-1
    list_data = {
        'total': len(reports_list),
        'list': split_report_list[index],
    }
    return HttpResponse(json.dumps(list_data))

def get_case_list(request):
    """
    根据传入的suite_id查询对应的case_list
    :param request:
    :return: case_list的信息
    """
    split_case_list = []
    case_list = []
    suite_id = request.GET['suiteId']
    case_data = TestCase.objects.filter(suite_id=suite_id, is_del=0).values()
    for _ in case_data:
        case_list.append(_)
    print case_list
    if len(case_list) > 0:
        for i in range(0, len(case_list), 10):
            split_case_list.append(case_list[i:i+10])
        print split_case_list
        index = int(request.GET['index'])-1
        case = {
            'total': len(case_list),
            'list': split_case_list[index],
        }
        return HttpResponse(json.dumps(case))
    return HttpResponse(json.dumps({'total': 0,'list': [],}))