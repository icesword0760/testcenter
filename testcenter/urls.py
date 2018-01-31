"""testcenter URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
# -*- coding: utf-8
from django.conf.urls import url
from django.contrib import admin
from apitest import views as apitest_view
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    #url(r'^$', apitest_view.test_load_case),
    url(r'^getprojectlist$', apitest_view.get_project_list),
    url(r'^addproject$', apitest_view.add_project),
    url(r'^getsuitelist$', apitest_view.get_suite_list),
    url(r'^getcaselist$', apitest_view.get_case_list),
    url(r'^addsuite$', apitest_view.add_suite),
    url(r'^addcase$', apitest_view.add_case),
    url(r'^getsuitedetail$', apitest_view.get_suite_detail),
    url(r'^getcasedetail$', apitest_view.get_case_detail),
    url(r'^updatesuite$', apitest_view.update_suite),
    url(r'^updatecase$', apitest_view.update_case),
    url(r'^delsuite$', apitest_view.del_suite),
    url(r'^delcase$', apitest_view.del_case),
    url(r'^runsuite$', apitest_view.run_suite),
    url(r'^getreport$', apitest_view.get_report),
    url(r'^getreportslist$', apitest_view.get_reports_list),
]
