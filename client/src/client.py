#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
client.py
~~~~~~~~~

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from copy import deepcopy
import json
import logging
from multiprocessing.managers import SyncManager
import os
import sys
import time

import numpy as np

from sampler import sensitivity_analysis


logging.basicConfig(level=logging.INFO)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

AUTHKEY = 'password'
J_per_kWh = 3600000

def make_job_json(i, sample):
    job = {'job': {'id': i, 'params': {key: value for key, value in sample}}}
    return json.dumps(job)


class JobQueueManager(SyncManager):
    pass


def make_creator_manager(server_ip, port, authkey):
    """Start a server manager on the given port, using the given authkey.
    """
    JobQueueManager.register('get_job_q')
    JobQueueManager.register('get_result_q')
    manager = JobQueueManager(address=(server_ip, port), authkey=authkey)
    manager.connect()
    return manager


def update_log(t0, done):
    logging.info("%.2f%% done" % done)
    t1 = time.time()
    secs = t1 - t0
    remaining = 100 - done
    secs_per_percent = secs / done
    secs_remaining = secs_per_percent * remaining
    logging.info("Approx %.1f mins remaining" % (secs_remaining / 60))


def main(server_ip):
    logging.info("Making creator manager")
    manager = make_creator_manager(server_ip, 50000, AUTHKEY)

    logging.debug("Getting queues")
    job_q = manager.get_job_q()
    result_q = manager.get_result_q()

    logging.debug("Getting jobs")
    # fill in details of the type of job to be run
    sensitivity_analysis(sample_method='saltelli', analysis_method='sobol', N=10)

    logging.info("Done")
    # TODO: kill the queue and worker/s
    for i in range(10):
        job_q.put('kill worker')
    time.sleep(5)


if __name__ == "__main__":
    logging.info("Starting job creator")
    server_ip = "queue"
    main(server_ip)
