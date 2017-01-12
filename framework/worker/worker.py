#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
worker.py
~~~~~~~~~
EnergyPlus worker. This contains the basic code required to watch a folder for
incoming jobs, then run them and place the results ready to be fetched by the
client.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import tempfile
import zipfile

from runner import run as eplus_run


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
JOBS_DIR = os.path.join(THIS_DIR, 'jobs')
RESULTS_DIR = os.path.join(THIS_DIR, 'results')


def get_jobs():
    """Pick up the jobs currently in the jobs directory.
    
    Returns
    -------
    list
        List of absolute paths to each zipped job.

    """
    jobs = [os.path.join(JOBS_DIR, job)
            for job in os.listdir(JOBS_DIR)]
    return jobs


def unzip_dir(src, dest=None, rm=False):
    """Unzip a zipped file.
    
    This is used for the incoming jobs.
    
    Parameters
    ----------
    src : str
        Path to the zip archive.
    dest : str, optional {default: None}
        The destination folder.
    rm : bool, optional {default: False}
        Flag indicating whether to delete the archive once unzipped.

    """
    with zipfile.ZipFile(src, 'r') as zf:
        zf.extractall(dest)
    if rm:
        os.remove(src)


def zip_dir(src, dest, rm=False, extensions=None):
    """Zip a directory.
    
    This is used for zipping results to be collected.
    
    src : str
        Path to the directory to be zipped.
    dest : str
        The destination zipped archive name.
    rm : bool, optional {default: False}
        Flag indicating whether to delete the source directory once zipped.
    extensions : list, optional {default: None}
        List of extensions to keep. If None, keeps all.

    """    
    pass


def main():
    while True:
        jobs = get_jobs()
        run_dir = tempfile.mkdtemp()
        if jobs:
            logging.debug('found %i jobs' % len(jobs))
            unzip_dir(jobs[0], run_dir)

            idf = os.path.join(run_dir, 'in.idf')
            epw = os.path.join(run_dir, 'in.epw')
            eplus_run(idf, epw, output_directory=RESULTS_DIR)
            # postprocess anything that needs it
            
    
    
if __name__ == "__main__":
    main()