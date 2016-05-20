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

from sampler import analyse
from sampler import samples 
from compiler.pyassem import DONE


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
    
#    names, runs, empty_results = samples('morris', N=1)
    names, runs, empty_results = samples('saltelli', N=100)
    jobs = enumerate(zip(names, (float(n) for n in run)) for run in runs)
    
    
    logging.debug("Initialising empty results")
    elec_results = deepcopy(empty_results)
    nonelec_results = deepcopy(empty_results)
    time_results = deepcopy(empty_results)

    step = 5 # percent complete
    last_step = 0
    t0 = time.time()
    while np.isnan(elec_results).any():
        try:
            job = make_job_json(*jobs.next())
            job_q.put(job)
        except:
            pass
        try:
            result = result_q.get_nowait()
            elec_results[result['id']] = result['electrical'] / J_per_kWh
            nonelec_results[result['id']] = result['non-electrical'] / J_per_kWh
            time_results[result['id']] = result['time']
            done = (float(result['id']) + 1) / len(elec_results) * 100
            if done > last_step + step:
                last_step += step
                update_log(t0, done)
        except:
            pass
    logging.info("Analysing results")
    #==========================================================================
    # analyse(runs, elec_results, 'elec.txt', method='morris')
    # analyse(runs, nonelec_results, 'nonelec.txt', method='morris')
    # analyse(runs, time_results, 'time.txt', method='morris')
    #==========================================================================
    analyse(runs, elec_results, 'elec.txt', method='sobol')
    analyse(runs, nonelec_results, 'nonelec.txt', method='sobol')
    analyse(runs, time_results, 'time.txt', method='sobol')
    logging.info("Done")
    # TODO: kill the queue and worker/s
    for i in range(10):
        job_q.put('kill worker')
    time.sleep(5)


if __name__ == "__main__":
    logging.info("Starting job creator")
    server_ip = "queue"
    main(server_ip)
