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
from __future__ import unicode_literals

import Queue
import json
import logging
from multiprocessing.managers import SyncManager
import os
import shutil
import sys
import tempfile
import traceback

from idfsyntax import prepare_idf

sys.path.append(os.getcwd())

from runner import RunnableIDF
from src import results


AUTHKEY = 'password'

logging.basicConfig(level=logging.INFO)
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
            traceback.print_exc()
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
                         expandobjects=True, verbose='q')
        except Exception as e:
            traceback.print_exc()
            epluserr = os.path.join(self.rundir, 'eplusout.err')
            with open(epluserr, 'r') as err:
                for line in err:
                    logging.error(line)
                
    def postprocess(self):
        """Stub to process and set the results.
        """
        eplussql = os.path.join(self.rundir, 'eplusout.sql')
        if self.job['daylighting'] > 0.5:
            idf = os.path.join(self.rundir, 'eplusout.expidf')
            err = os.path.join(self.rundir, 'eplusout.err')
            sql = os.path.join(self.rundir, 'eplusout.sql')
            shutil.copy(idf, '/tmp/results/daylighting.idf')
            shutil.copy(err, '/tmp/results/daylighting.err')
            shutil.copy(sql, '/tmp/results/daylighting.sql')
        elec = results.get_elec(eplussql)
        non_elec = results.get_non_elec(eplussql)
        eplusend = os.path.join(self.rundir, 'eplusout.end')
        execution_time = results.get_execution_time(eplusend)
        self.result = {'id': self.id,
                       'electrical': elec, 
                       'non-electrical': non_elec,
                       'time': execution_time,
                       }


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
    JobQueueManager.register(b'get_job_q')
    logging.debug("Registering results queue")
    JobQueueManager.register(b'get_result_q')
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
            if next_job == 'kill worker':
                exit()
        except Queue.Empty:
            continue
        job = EPlusJob(next_job)
        result_q.put(job.result)
        logging.debug(str(job.result))

    
if __name__ == "__main__":
    server_ip = "queue"
    main(server_ip)
