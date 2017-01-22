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
import sys

from manager.src.distribute import find_server
from manager.src.distribute import is_available
from manager.src.distribute import ping
from manager.src.distribute import sweep_results
from manager.src.sensitivity import samples
from manager.src.config import config
from manager.src.ssh_lib import sshCommandNoWait


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(THIS_DIR, os.pardir)))

QUEUE_SERVER = os.path.join(
    THIS_DIR, os.pardir, os.pardir, 'queue/src/queue.py')


def test_config_smoketest():
    """Just test everything is imported correctly and a dict is returned.
    """
    job_type = config.get('Client', 'job_type')
    options = config.items(job_type)
    options = {item[0]: item[1] for item in options}  # make into a dict
    assert isinstance(options, dict)
    

def test_samples_smoketest():
    """Just test everything is imported correctly and a tuple is returned.
    """
    job_type = config.get('Client', 'job_type')
    options = config.items(job_type)
    options = {item[0]: item[1] for item in options}  # make into a dict
    assert isinstance(samples(**options), list)


def clear_queue(q):
    """Ensure the queue is empty before running a test.
    """
    while True:
        try:
            q.get_nowait()
        except Empty:
            return


def test_sweep_results():
    """Smoke test.
    """
    sweep_results()
    
    
def test_ping():
    result = ping('google.com', 1)
    assert result


def test_is_available():
    address = '52.214.221.169'
    remote_config = {
        "sshKeyFileName": config.get('Client', 'sshKeyFileName'),
        "serverUserName": config.get('Client', 'serverUserName'),
        "serverAddress": address}
    sshCommandNoWait(remote_config, 'touch ready.txt')
    assert is_available(address, remote_config)
    sshCommandNoWait(remote_config, 'rm ready.txt')
    assert not is_available(address, remote_config)


def test_find_server():
    remote_config = {
        "sshKeyFileName": config.get('Client', 'sshKeyFileName'),
        "serverUserName": config.get('Client', 'serverUserName'),
        "serverAddress": None}
    expected = '52.210.46.10'
    result = find_server(remote_config)
    assert result == expected

        
