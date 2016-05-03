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

import logging
from multiprocessing.managers import SyncManager
import os
import sys
import time
from eppy.modeleditor import IDF


logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

VERSION = os.environ['ENERGYPLUS_VERSION'].replace('.', '-')
EPLUS_HOME = "/usr/local/EnergyPlus-{VERSION}".format(**locals())
EPLUS_EXE = os.path.join(EPLUS_HOME, 'energyplus')
EPLUS_IDD = os.path.join(EPLUS_HOME, 'Energy+.idd')
 
EPLUS_WEATHER = os.path.join(EPLUS_HOME, 'WeatherData')
THIS_DIR = os.path.abspath(os.path.dirname(__file__))
EPW_TO_RUN = os.path.join(THIS_DIR, 'in_weather.epw')

AUTHKEY = 'password'

IDD = os.path.join(EPLUS_HOME, 'Energy+.idd')
IDF.setiddname(IDD)


class EPlusJob(object):
    
    def __init__(self, job):
        """Template to run an EnergyPlus job.
        """
        self.job = job
        self.preprocess()
        self.run()
        self.postprocess()

    def preprocess(self):
        """Stub to build the IDF (use eppy).
        """
        self.idf = self.job

    def run(self):
        """Stub to run the IDF.
        """
        self.raw_results = self.idf

    def postprocess(self):
        """Stub to process and set the results.
        """
        self.result = self.raw_results


class JobQueueManager(SyncManager):
    """Handle connections to the  jobs queue and results queue.
    """
    pass


def make_client_manager(server_ip, port, authkey):
    """Create a client manager.
    
    Parameters
    ----------
    server_ip : str
        IP address of the server managing the jobs and results queues.
    port : int
        Port number to connect to.
    authkey : str
        Password to authenticate the connection.
    
    Returns
    -------
    JobQueueManager object

    """
    logging.debug("Registering job queue")
    JobQueueManager.register('get_job_q')
    logging.debug("Registering results queue")
    JobQueueManager.register('get_result_q')
    manager = JobQueueManager(address=(server_ip, port), authkey=authkey)
    logging.debug("Connecting to manager")
    try:
        manager.connect()
    except Exception as e:
        logging.error("Error: %s" % e)
    return manager

def main(server_ip):
    logging.debug("Making client manager")
    manager = make_client_manager(server_ip, 50000, AUTHKEY)
    logging.debug("Getting queues")
    job_q = manager.get_job_q()
    result_q = manager.get_result_q()
    while True:
        try:
            job = EPlusJob(job_q.get_nowait())
            result_q.put('Done: {}'.format(job.result))
        except:
            pass

    
if __name__ == "__main__":
    server_ip = "queue" 
    main(server_ip)
