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

import json
import logging
from multiprocessing.managers import SyncManager
import os
import Queue
import sys
import tempfile

sys.path.append(os.getcwd())

from src import results
from src.idfsyntax import prepare_idf
from src.runner import RunnableIDF


AUTHKEY = 'password'

logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)


class EPlusJob(object):
    
    def __init__(self, job):
        """Template to run an EnergyPlus job.
        """
        job = json.loads(job)
        self.job = job['job']['params']
        self.id = job['job']['id']
        logging.debug("Creating IDF")
        try:
            self.preprocess()
        except Exception as e:
            logging.debug(e)
        logging.debug("Running IDF")      
        self.run()
        logging.debug("Processing results")
        try:
            self.postprocess()
        except Exception as e:
            logging.error(e)
            raise

    def preprocess(self):
        """Stub to build the IDF (use eppy).
        """
        # get the IDF into eppy
        idf = RunnableIDF(
            './data/template.idf', None)
        # make the required changes
        idf = prepare_idf(idf, self.job)
        self.idf = idf

    def run(self):
        """Stub to run the IDF.
        """
        self.rundir = tempfile.gettempdir()
        try:
            self.idf.run(output_directory=self.rundir, readvars=True, 
                         expandobjects=True)
        except Exception as e:
            logging.debug(e)
            epluserr = os.path.join(self.rundir, 'eplusout.err')
            with open(epluserr, 'r') as err:
                for line in err:
                    logging.debug(line)
        logging.debug("rundir files: %s", str(os.listdir(self.rundir)))
                
    def postprocess(self):
        """Stub to process and set the results.
        """
        eplussql = os.path.join(self.rundir, 'eplusout.sql')
        elec = results.get_elec(eplussql)
        non_elec = results.get_non_elec(eplussql)
        self.result = {'id': self.id,
                       'electrical': elec, 
                       'non-electrical': non_elec}


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
        logging.error("%s: %s" % (sys.exc_info()[0], e))
    return manager


def main(server_ip):
    logging.debug("Making client manager")
    manager = make_client_manager(server_ip, 50000, AUTHKEY)
    logging.debug("Getting queues")
    job_q = manager.get_job_q()
    result_q = manager.get_result_q()
    while True:
        try:
            next_job = job_q.get_nowait()
            logging.debug(next_job)
            job = EPlusJob(next_job)
            result_q.put(job.result)
            logging.debug(str(job.result))
        except Queue.Empty:
            pass

    
if __name__ == "__main__":
    server_ip = "queue"
    main(server_ip)
