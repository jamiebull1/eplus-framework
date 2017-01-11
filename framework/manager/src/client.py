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
from multiprocessing.managers import SyncManager
import time

import os
import sys

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(THIS_DIR, os.pardir)))

from src.sensitivity import sensitivity_analysis
from src.config import config


logging.basicConfig(level=logging.INFO)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

AUTHKEY = 'password'


class JobQueueManager(SyncManager):
    pass


def make_creator_manager(server_ip, port, authkey):
    """Start a server manager on the given port, using the given authkey.
    """
    JobQueueManager.register(b'get_job_q')
    JobQueueManager.register(b'get_result_q')
    manager = JobQueueManager(address=(server_ip, port), authkey=authkey)
    manager.connect()
    return manager

def get_config():
    options = {'sample_method': config.get('Sensitivity', 'sample_method'),
               'analysis_method': config.get('Sensitivity', 'analysis_method'),
               'N': config.getint('Sensitivity', 'N'),
               'second_order': config.getboolean('Sensitivity', 'second_order'),
               }
    return options
    
def main(server_ip):
    logging.info("Making creator manager")
    manager = make_creator_manager(server_ip, 50000, AUTHKEY)

    logging.debug("Getting queues")
    job_q = manager.get_job_q()
    result_q = manager.get_result_q()

    logging.debug("Getting jobs")
    # get details of the type of job to be run
    options = get_config()
    sensitivity_analysis(
        job_q, result_q,
        **options         #=======================================================================
        # sample_method=sample_method, 
        # analysis_method=analysis_method,
        # N=N,
        # second_order=second_order,
        #=======================================================================
        )

    logging.info("Done")
    # TODO: kill the queue and worker/s
    for i in range(10):
        job_q.put('kill worker')
    time.sleep(5)


if __name__ == "__main__":
    logging.info("Starting job creator")
    server_ip = "queue"
    main(server_ip)
