# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import HttpResponse
from django.shortcuts import render

from .cov import cov

def start_coverage(request):
    cov.start()
    return HttpResponse('Started data collection for code coverage')

def stop_coverage(request):
    cov.stop()
    cov.save()
    cov.combine()
    cov.html_report()
    return HttpResponse('Stopped and saved data from code coverage')

def report(request):
    return HttpResponse('TBD')
