"""
distribute.py
~~~~~~~~~~~~~
Package jobs into zip archives and send them to be processed.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import tempfile

from eppy.modeleditor import IDF
from framework.manager.src.ssh_lib import sftpSendFile


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(THIS_DIR, os.pardir, 'data')
IDF.setiddname(os.path.join(DATA_DIR, 'idd/Energy+.idd'))

JOBQUEUE = os.path.join(THIS_DIR, os.pardir, os.pardir, 'queue', 'job_queue')


def make_job():
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


def find_server():
    """Find the next server with an available CPU.
    """    
    pass


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
