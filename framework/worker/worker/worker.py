#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
worker.py
~~~~~~~~~

EnergyPlus worker. This contains an EPlusJob object consisting of stubs to be
filled out to preprocess, run, and postprocess a job fetched from the queue
container, and return the results back to the queue container.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import tempfile
import zipfile

from runner import run


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
JOBS_DIR = os.path.join(THIS_DIR, os.pardir, 'jobs')


def get_jobs():
    jobs = os.listdir(JOBS_DIR)
    return jobs


def unzip(archive, rundir):
    archive = os.path.join(JOBS_DIR, archive)
    with zipfile.ZipFile(archive, 'r') as zf:
        zf.extractall(rundir)


def main():
    while True:
        jobs = get_jobs()
        run_dir = tempfile.mkdtemp()
        if jobs:
            logging.debug('found %i jobs' % len(jobs))
            unzip(jobs[0], run_dir)
            idf = os.path.join(run_dir, 'in.idf')
            epw = os.path.join(run_dir, 'in.epw')
            output_dir = '.'
            run(idf, epw, output_directory='../results')
    
    
if __name__ == "__main__":
    main()