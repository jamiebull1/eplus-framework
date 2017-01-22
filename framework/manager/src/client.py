#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
client.py
~~~~~~~~~

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time

from framework.manager.src.distribute import distribute_job
from framework.manager.src.distribute import sweep_results
from framework.manager.src.jobgenerator import getjobs


logging.basicConfig(level=logging.INFO)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)
   

def main():
    """The main entry point for the program.
    
    This orchestrates the creation of jobs based on the contents of the
    client.cfg file.
    
    """
    # call the function defined, which should return a generator
    # the generator should contain directory paths to fully-built jobs, ready
    # to be distributed for processing
    for job in getjobs():
        # this blocks until a resource becomes available
        distribute_job(job)
        # TODO: store the results while running
        
    # Keep sweeping until all results are in
    running_jobs = sweep_results()
    while running_jobs > 0:
        running_jobs = sweep_results()
        time.sleep(5)
        # TODO: store the final sets of results
    # TODO: post-process the results
    logging.info("Done")


if __name__ == "__main__":
    main()