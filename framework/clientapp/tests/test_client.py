# Copyright (c) 2017 Jamie Bull
# =======================================================================
#  Distributed under the MIT License.
#  (See accompanying file LICENSE or copy at
#  http://opensource.org/licenses/MIT)
# =======================================================================
"""pytest for eplus-framework client"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from Queue import Empty
import os
import subprocess
import sys

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(THIS_DIR, os.pardir)))

from clientapp.src.client import get_config
from clientapp.src.client import make_creator_manager
from clientapp.src.sensitivity import samples


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
