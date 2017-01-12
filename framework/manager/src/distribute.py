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
import tempfile
import time

from eppy.modeleditor import IDF
from framework.manager.src.config import config
from framework.manager.src.ssh_lib import sftpSendFile
from manager.src import ssh_lib


logging.basicConfig(level=logging.INFO)

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(THIS_DIR, os.pardir, 'data')
IDF.setiddname(os.path.join(DATA_DIR, 'idd/Energy+.idd'))

JOBQUEUE = os.path.join(THIS_DIR, os.pardir, os.pardir, 'queue', 'job_queue')


def distribute_job(jobpath):
    # TODO: add a name for the job
    enqueue_job(jobpath, JOBQUEUE)
    
    send_job()


def package_job():
    """Package an IDF and schedules file in a temporary directory.
    
    This is just as a dummy job for now for testing remote servers.
    
    Returns
    -------
    str
        Path to the temp directory containing job resources.
    
    """
    idfpath = os.path.join(DATA_DIR, 'idfs/smallfile.idf')
    csvpath = os.path.join(DATA_DIR, 'schedule_csv/dummy.csv')
    epwpath = os.path.join(DATA_DIR, 'weather/islington/cntr_Islington_TRY.epw')
    idf = IDF(idfpath)
    idf.outputtype = 'nocomment2'
    build_dir = tempfile.mkdtemp()
    shutil.copy(csvpath, build_dir)
    shutil.copy(epwpath, os.path.join(build_dir, 'in.epw'))
    idf.saveas(os.path.join(build_dir, 'in.idf'))

    return build_dir


def enqueue_job(src, dest):
    """Zip and send a job folder to a queue folder.
    
    Parameters
    ----------
    src : str
        Path to a directory containing job files.
    path : str
        Queue directory to send the job to.

    """
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
    sftpSendFile(remote_config, localpath, remotepath)
    os.remove(localpath)


def find_server(remote_config, timeout_secs=3600):
    """Find the first available server.

    Parameters
    ----------
    remote_config : dict
        Configurations details.
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

                return address

        tour_count += 1
        time.sleep(polling_wait_secs)

    return address


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


def test_ping():
    result = ping('google.com', 1)
    assert result


def test_is_available():
    address = '52.210.46.10'
    remote_config = {
        "sshKeyFileName": config.get('Client', 'sshKeyFileName'),
        "serverUserName": config.get('Client', 'serverUserName'),
        "serverAddress": address}
    ssh_lib.sshCommandNoWait(remote_config, 'touch ready.txt')
    assert is_available(address, remote_config)
    print(ssh_lib.sshCommandNoWait(remote_config, 'rm ready.txt'))
    assert not is_available(address, remote_config)


def test_find_server():
    remote_config = {
        "sshKeyFileName": config.get('Client', 'sshKeyFileName'),
        "serverUserName": config.get('Client', 'serverUserName'),
        "serverAddress": None}
    expected = '52.210.46.10'
    result = find_server(remote_config)
    assert result == expected
