"""
distribute.py
~~~~~~~~~~~~~
Package jobs into zip archives and send them to be processed.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import platform
import shutil
import subprocess
import time

from eppy.modeleditor import IDF

from manager.src.ssh_lib import sftpGetDirFiles
from manager.src.ssh_lib import sshCommandNoWait
from manager.src.ssh_lib import sshCommandWait
from manager.src import ssh_lib
from manager.src.config import config
from manager.src.ssh_lib import sftpSendFile


logging.basicConfig(level=logging.INFO)

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(THIS_DIR, os.pardir, 'data')
IDF.setiddname(os.path.join(DATA_DIR, 'idd/Energy+.idd'))

JOBQUEUE = os.path.join(THIS_DIR, os.pardir, os.pardir, 'queue', 'job_queue')
RESULTS = os.path.join(THIS_DIR, os.pardir, os.pardir, 'queue', 'results_queue')


def distribute_job(jobpath):
    """Find a server on which to run an EnergyPlus simulation.
    
    Parameters
    ----------
    jobpath : str
        Path to a folder containing everything needed to run the simulation.

    """
    jobdir = os.path.basename(jobpath)
    queuedir = os.path.join(JOBQUEUE, jobdir)
    enqueue_job(jobpath, queuedir)
    remotepath = 'eplus_worker/worker/jobs/%s.zip' % jobdir
    remote_config = find_server()
    send_job(remote_config, queuedir + '.zip', remotepath)
    logging.info('Job sent: %s ' % jobdir)


def enqueue_job(src, dest):
    """Zip and send a job folder to a queue folder.
    
    Parameters
    ----------
    src : str
        Path to a directory containing job files.
    path : str
        Queue directory to send the job to.

    """
    logging.info('Queueing job %s to %s' % (src, dest))
    shutil.make_archive(dest, 'zip', src)
    shutil.rmtree(src)  # tidy up the temporary directory


def send_job(remote_config, localpath, remotepath):
    """Send a job to a remote server for processing.
    
    Parameters
    ----------
    remote_config : dict
        Parameters of the remote server.
    localpath : str
        Path to the zipped job.
    remotepath : str
        Path to send to on the remote server.

    """
    logging.info('Sending job %s to %s' % (localpath, remotepath))
    sftpSendFile(remote_config, localpath, remotepath)
    os.remove(localpath)


def find_server(timeout_secs=3600):
    """Find the first available server.

    Parameters
    ----------
    timeout_mins : int, optional
        Time to allow for polling. This needs to be fairly high (default: 60)
        since simulations can take a long time to complete.

    Returns
    -------
    int
        The DNS name or IP address of the server acquired in the list of serves.

    Raises
    ------
    Exception : timeout error

    """
    remote_config = {
        "sshKeyFileName": config.get('Client', 'sshKeyFileName'),
        "serverUserName": config.get('Client', 'serverUserName'),
        "serverAddress": None}
    servers = config.get('Client', 'serverAddresses').split()
    logging.info(
        "There are currently {} servers configured".format(len(servers)))
    servers = set(s for s in servers if ping(s))
    logging.info("{} servers responding to ping".format(len(servers)))
    if not servers:
        time.sleep(min(timeout_secs, 30))
        raise Exception("no servers responding to ping")

    tour_count = 0

    polling_wait_secs = min(timeout_secs, 30)  # wait n seconds between polls
    max_tour_count = timeout_secs / polling_wait_secs
    while tour_count < max_tour_count:
        for address in servers:
            if is_available(address, remote_config):
                _o, _e = ssh_lib.sshCommandWait(remote_config, 'rm ready.txt')
                servers.remove(address)
                logging.info("Acquired {}".format(address))

                return remote_config
        sweep_results()  # we need to try and clear any space
        tour_count += 1
        time.sleep(polling_wait_secs)

    return remote_config


def is_available(address, remote_config, timeout=None):
    """Check if an IP address is available.
    
    Parameters
    ----------
    address : str
        Public DNS name or IP address.
    remote_config : dict
        Configurations details.
    
    Returns
    -------
    bool
    
    """
    remote_config['serverAddress'] = address
    files = ssh_lib.sshCommandWait(remote_config, 'ls', timeout=timeout)[0]
    if 'ready.txt\n' in files:
        return True
    else:
        return False


def ping(address, count=4):
    """Try to ping a given server address.

    Parameters
    ----------
    address : str
        The address to ping.
    count : int, optional
        How many times to ping {default: 4)

    Returns
    -------
    bool

    """
    try:
        if platform.system() == 'Windows':
            num_flag = '-n'
        else:
            num_flag = '-c'
        subprocess.check_call(['ping', num_flag, str(count), address])
        return True
    except subprocess.CalledProcessError:
        return False


def sweep_results():
    """Fetch completed jobs from servers and report number of running jobs.
    
    Returns
    -------
    int
        Number of jobs currently running.

    """
    remote_config = {
        "sshKeyFileName": config.get('Client', 'sshKeyFileName'),
        "serverUserName": config.get('Client', 'serverUserName'),
        "serverAddress": None}
    servers = config.get('Client', 'serverAddresses').split()
    jobspath = 'eplus_worker/worker/jobs'
    resultspath = 'eplus_worker/worker/results'
    num_running_jobs = 0
    for address in servers:
        logging.info('Sweeping results from %s' % address)
        remote_config['serverAddress'] = address
        waiting_jobs = sshCommandWait(remote_config, 'ls %s' % jobspath)
        num_running_jobs += len(waiting_jobs[0])
        dirs = sshCommandWait(remote_config, 'ls %s' % resultspath)
        num_running_jobs += len(dirs[0])
        for d in dirs[0]:
            d = d.strip()
            results_dir = '%s/%s' % (resultspath, d)
            files = sshCommandWait(remote_config, 'ls %s/%s' % (resultspath, d))
            if 'eplusout.end\n' in files[0]:
                local_results_dir = os.path.join(RESULTS, d)
                logging.info('Fetching %s' % results_dir)
                os.mkdir(local_results_dir)
                sftpGetDirFiles(remote_config, results_dir, local_results_dir)
                sshCommandNoWait(remote_config, 'rm -rf %s' % results_dir)
                num_running_jobs -= 1
            logging.info('Current running jobs: %i' % num_running_jobs)
    return num_running_jobs
