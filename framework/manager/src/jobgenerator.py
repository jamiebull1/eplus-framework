"""
jobgenerator.py
~~~~~~~~~~~~~~~
Module containing the top level code for job generator functions.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from manager.src.config import config
from manager.src.idfsyntax import prepare_idf
from manager.src import sensitivity


logging.basicConfig(level=logging.INFO)

WHITELIST = ['sensitivity_analysis']


def getjobs():
    # find the type of job from the config file
    # create specifications for creating jobs as a list
    jobs = job_specs()  # get from somewhere
    while jobs:
        jobspec = jobs.pop()  # get a job
        job = prepare_idf(jobspec)  # returns path to a temp dir with the job
        yield job


def job_specs():
    job_type = config.get('Client', 'job_type')
    options = config.items(job_type)
    options = {item[0]: item[1] for item in options}  # make into a dict
    func = options.pop('func')  # grab the job spec generation function
    if func not in WHITELIST:
        logging.error('%s is not a white-listed function' % func)
        raise ValueError
    specs = eval(func)(**options)
    return specs


def sensitivity_analysis(*args, **kwargs):
    """Generate job specs for sensitivity analysis - Saltelli or Morris.
    """
    geometry = kwargs.pop('geometry')
    specs = sensitivity.samples(**kwargs)
    for job in specs:
        job.update({'geometry': geometry})
    return specs


def test_getjobs():
    jobs = getjobs()
    for job in jobs:
        print(job)


def test_job_specs():
    print(job_specs())
