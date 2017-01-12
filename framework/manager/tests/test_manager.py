# Copyright (c) 2017 Jamie Bull
# =======================================================================
#  Distributed under the MIT License.
#  (See accompanying file LICENSE or copy at
#  http://opensource.org/licenses/MIT)
# =======================================================================
"""pytest for eplus-framework manager"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from Queue import Empty
import os
import shutil
import subprocess
import sys

from framework.manager.src.distribute import JOBQUEUE
from framework.manager.src.distribute import enqueue_job
from framework.manager.src.distribute import package_job
from framework.manager.src.distribute import send_job
from framework.manager.src.ssh_lib import sshCommandWait
from manager.src.client import get_config
from manager.src.client import make_creator_manager
from manager.src.sensitivity import samples


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(THIS_DIR, os.pardir)))



SERVER_IP = 'queue'
PORTNUM = 50000
AUTHKEY = 'password'

QUEUE_SERVER = os.path.join(
    THIS_DIR, os.pardir, os.pardir, 'queue/src/queue.py')


def test_config_smoketest():
    """Just test everything is imported correctly and a dict is returned.
    """
    options = get_config()
    assert isinstance(options, dict)
    

def test_samples_smoketest():
    """Just test everything is imported correctly and a tuple is returned.
    """
    options = get_config()
    assert isinstance(samples(**options), tuple)


def clear_queue(q):
    """Ensure the queue is empty before running a test.
    """
    while True:
        try:
            q.get_nowait()
        except Empty:
            return


class TestQueues():
    
    def setup(self):
        """Create a queue server.
        """
        self.server = subprocess.Popen('python %s' % QUEUE_SERVER)
    
    def teardown(self):
        """Kill the queue server.
        """
        self.server.terminate()
        
    def test_creator_manager_job(self):
        """Test that we can add and receive jobs from the job queue.
        """
        manager = make_creator_manager(SERVER_IP, PORTNUM, AUTHKEY)
        job_q = manager.get_job_q()
        clear_queue(job_q)
        jobs = ['foo', 'bar', 'baz']
        for job in jobs:
            job_q.put(job)
        for job in jobs:
            assert job_q.get_nowait() == job
                
    def test_creator_manager_result(self):
        """Test that we can add and receive jobs from the results queue.
        """
        manager = make_creator_manager(SERVER_IP, PORTNUM, AUTHKEY)
        result_q = manager.get_result_q()
        clear_queue(result_q)
        results = ['foo', 'bar', 'baz']
        for result in results:
            result_q.put(result)
        for result in results:
            assert result_q.get_nowait() == result
    
    def test_queue_is_consumed(self):
        """Test that when we add stuff to the queue that workers take from it.
        """
        manager = make_creator_manager(SERVER_IP, PORTNUM, AUTHKEY)
        job_q = manager.get_job_q()
        clear_queue(job_q)
        jobs = ['foo', 'bar', 'baz']
        for job in jobs:
            job_q.put(job)
        
        
class TestDummyJob:

    def setup(self):
        """Create common resources.
        """
        self.testjob = os.path.join(JOBQUEUE, 'test')
        self.testjobzip = os.path.join(JOBQUEUE, 'test.zip')
        self.remote_config = {
            "sshKeyFileName": 'C:/Users/Jamie/oco_key.pem',
            "serverUserName": 'ec2-user',
            "serverAddress": '52.210.46.10'}
        self.remotejobzip = 'eplus_worker/worker/jobs/job.zip'

    def teardown(self):
        """Tidy up residual files locally and remotely.
        """
        try:
            shutil.rmtree(self.testjob + '.zip')
        except OSError:
            pass
        sshCommandWait(self.remote_config, 'rm %s' % self.remotejobzip)
        res = sshCommandWait(self.remote_config, 'ls %s' % self.remotejobzip)
        assert self.remotejobzip + '\n' not in res[0]
        
    def test_package_job(self):
        """Test creating a job. Fails if expected files are not in the tempdir.
        """
        result = package_job()
        assert os.path.isdir(result)
        expected = set(['dummy.csv', 'in.epw', 'in.idf'])
        result = set(os.listdir(result))
        assert result == expected
    
    def test_enqueue_job(self):
        """
        """
        build_dir = package_job()
        enqueue_job(build_dir, self.testjob)
        assert os.path.isfile(self.testjobzip)
        assert not os.path.isdir(build_dir)
    
    def test_send_job(self):
        """
        """
        build_dir = package_job()
        enqueue_job(build_dir, self.testjob)
        send_job(self.remote_config, self.testjobzip, self.remotejobzip)
        res = sshCommandWait(self.remote_config, 'ls %s' % self.remotejobzip)
        assert self.remotejobzip + '\n' in res[0]
        
        
