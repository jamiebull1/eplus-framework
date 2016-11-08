#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
queue.py
~~~~~~~~

Module to handle a pair of queues of EnergyPlus models and of EnergyPlus 
results by distributing them to computing resources, either locally or 
remotely.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from Queue import Queue as _Queue
from functools import partial
import logging
from multiprocessing.managers import SyncManager
import socket


logging.basicConfig(level=logging.INFO)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

PORTNUM = 50000
AUTHKEY = 'password'
IP = socket.gethostbyname(socket.gethostname())


class JobQueueManager(SyncManager):
    pass


def make_server_manager(port, authkey):
    """Start a server manager on the given port, using the given authkey.
    """
    job_q = Queue()
    result_q = Queue()
    JobQueueManager.register(b'get_job_q', callable=partial(get_q, job_q))
    JobQueueManager.register(b'get_result_q', callable=partial(get_q, result_q))
    manager = JobQueueManager(address=('', port), authkey=authkey)
    logging.info("Running server on %s:%s" % (IP, PORTNUM))
    return manager


def get_q(q):
    return q


class Queue(_Queue):
    """
    A picklable queue which overrides the built-in Queue.Queue (which is
    imported as _Queue).
    """   
    
    def __getstate__(self):
        # Only pickle the state we care about
        return (self.maxsize, self.queue, self.unfinished_tasks)

    def __setstate__(self, state):
        # Re-initialize the object, then overwrite the default state with
        # our pickled state.
        Queue.__init__(self)
        self.maxsize = state[0]
        self.queue = state[1]
        self.unfinished_tasks = state[2]

    def get_nowait(self):
        """Intercept Queue.get_nowait so we can log it.
        
        Remove and return an item from the queue without blocking.

        Only get an item if one is immediately available. Otherwise
        raise the Empty exception.
        """
        got = self.get(False)  # in case we need to do something with it
        return got


if __name__ == "__main__":
    logging.info("Starting job server")
    manager = make_server_manager(PORTNUM, AUTHKEY)
    server = manager.get_server()
    server.serve_forever()
