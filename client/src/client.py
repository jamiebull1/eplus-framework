#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
client.py
~~~~~~~~~

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
from multiprocessing.managers import SyncManager
import os
import sys

sys.path.append(os.getcwd())

from src.sampler import samples


logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

AUTHKEY = 'password'

def make_job_json(sample):
    job = {'job': {'params': {key: value for key, value in sample}}}
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


def main(server_ip):
    logging.info("Making creator manager")
    manager = make_creator_manager(server_ip, 50000, AUTHKEY)
    logging.debug("Getting queues")
    job_q = manager.get_job_q()
    result_q = manager.get_result_q()
    jobs = samples()
    while True:
        try:
            job = make_job_json(jobs.next())
            job_q.put(job)
        except:
            pass
        try:
            result = result_q.get_nowait()
            logging.debug(result)
        except:
            pass


if __name__ == "__main__":
    logging.info("Starting job creator")
    server_ip = "queue" 
    main(server_ip)
