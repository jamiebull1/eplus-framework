"""
ssh_lib.py
~~~~~~~~~~
Wrapper for paramiko functions. Based on Brian Coffey's work for SimStock.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import paramiko as pm
import sys, time


def establishSSHconnection(remote_config):
    """Create an SSH connection.
    
    Parameters
    ----------
    remote_config : dict
        Dictionary containing sshKeyFileName, serverAddress and serverUserName.
    
    Returns
    -------
    SSHClient object
    
    """
    rsaKey = pm.RSAKey.from_private_key_file(remote_config['sshKeyFileName'])
    ssh = pm.SSHClient()
    ssh.set_missing_host_key_policy(pm.AutoAddPolicy())
    totalTime = 0 
    connected = False
    while not connected:
        try:
            ssh.connect( remote_config['serverAddress'], 
                         username = remote_config['serverUserName'], 
                         pkey = rsaKey )
            connected = True
        except Exception as e: 
            print(e)
            sys.stdout.write(".")
            time.sleep(1)
            totalTime += 1
            if totalTime >= 300:
                sys.stdout.write( "Timed out trying to connect to server.\n" )
                break
    return ssh


def sshCommandWait(remote_config, cmd, timeout=None):
    ssh = establishSSHconnection(remote_config)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout)
    stdout = stdout.readlines()
    stderr = stderr.readlines()
    ssh.close()
    return stdout, stderr


def sshCommandNoWait(remote_config, cmd):
    ssh = establishSSHconnection(remote_config)
    ssh.exec_command(cmd)
    ssh.close()


def sftpSendFile(remote_config, localFile, remoteFile):
    ssh = establishSSHconnection(remote_config)
    ftp = ssh.open_sftp()
    try:
        ftp.put(localFile,remoteFile)
    except:
        raise
    finally:
        ftp.close()
        ssh.close()
    
    
def sftpGetFile(remote_config, remoteFile, localFile):
    ssh = establishSSHconnection(remote_config)
    ftp = ssh.open_sftp()
    try:
        ftp.get(remoteFile,localFile)
        return True
    except:
        return False
    finally:
        ftp.close()
        ssh.close()


def sftpGetDirs(remote_config, remoteDir, localDir):
    ssh = establishSSHconnection(remote_config)
    ftp = ssh.open_sftp()
    try:
        for item in ftp.listdir(remoteDir):
            try:
                files = ftp.listdir('/'.join([remoteDir, item]))
            except IOError:
                continue
            try:
                os.mkdir(os.path.join(localDir, item))
            except OSError:
                pass
            for f in files:
                ftp.get('/'.join([remoteDir, item, f]),
                        os.path.join(localDir, item, f))
    except:
        raise
    finally:
        ftp.close()
        ssh.close()
