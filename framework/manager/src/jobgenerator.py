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

from sqlalchemy.exc import IntegrityError

from framework.manager.src.db_lib import insert
from manager.src import sensitivity
from manager.src.config import config
from manager.src.idfsyntax import prepare_idf


logging.basicConfig(level=logging.INFO)

WHITELIST = ['sensitivity_analysis']


def getjobs():
    # find the type of job from the config file
    # create specifications for creating jobs as a list
    jobs = job_specs()
    while jobs:
        jobspec = jobs.pop()  # get a job
        job = prepare_idf(jobspec)  # returns path to a build dir with the job
        store_params('postgis', 'sdb', 'job', jobspec)
        yield job


def job_specs():
    job_type = config.get('Client', 'job_type')
    options = config.items(job_type)
    options = {item[0]: item[1] for item in options}  # make into a dict
    store_params('postgis', 'sdb', 'options', options)
    func = options.pop('func')  # grab the job spec generation function
    if func not in WHITELIST:
        logging.error('%s is not a white-listed function' % func)
        raise ValueError
    specs = eval(func)(**options)
    return specs


def store_params(db, schema, table, params):
    params.update({'uid': dict_hash(params)})
    try:
        insert(db, schema, table, params)
    except IntegrityError:
        logging.debug(
            """Current parameters are already in the {table} table
            """.format(**locals()))


def dict_hash(adict):
    return str((hash(frozenset(adict.items()))))
    

def sensitivity_analysis(*args, **kwargs):
    """Generate job specs for sensitivity analysis - Saltelli or Morris.
    """
    geometry = kwargs.pop('geometry')
    specs = sensitivity.samples(**kwargs)
    for id_no, job in enumerate(specs):
        job.update({'geometry': geometry, 'id_no': id_no})
        job.update({'uid': dict_hash(job)})
        job.update({'id_no': id_no})  # this must happen after the unique ID
    return specs
