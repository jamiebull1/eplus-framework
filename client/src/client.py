#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
from multiprocessing.managers import SyncManager
import time


logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

AUTHKEY = 'password'

class JobQueueManager(SyncManager):
    pass

def make_creator_manager(server_ip, port, authkey):
    JobQueueManager.register('get_job_q')
    JobQueueManager.register('get_result_q')
    manager = JobQueueManager(address=(server_ip, port), authkey=authkey)
    manager.connect()
    return manager

def make_job_json(i):
    logging.debug('%i' % i)
    return {'job': i}

def main(server_ip):
    logging.info("Making creator manager")
    manager = make_creator_manager(server_ip, 50000, AUTHKEY)
    logging.debug("Getting queues")
    job_q = manager.get_job_q()
    result_q = manager.get_result_q()
    i = 0
    while True:
        i += 1
        job = make_job_json(i)
        job_q.put(job)
        time.sleep(1)
        try:
            result = result_q.get_nowait()
            logging.debug(result)
        except:
            pass

if __name__ == "__main__":
    logging.info("Starting job creator")
    server_ip = "queue" 
    main(server_ip)
