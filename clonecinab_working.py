#!/usr/bin/python
import os
import sys
import time
import socket
import logging
import smtplib
import subprocess as sp
import multiprocessing as mp
from optparse import OptionParser
from datetime import datetime, timedelta

""" Usage:
Multiple destinations, same source, gets full contents of source -
./cinabclone.py -s /media/HCP-Q1-Source -f ~/devices.list

## dest_file.txt contents ##
sdb
sdc
sdd
"""

## TO-DO
#    Email results - need to wait for all processes to finish
#    Log elalpsed times

## OPTION PARSER ##
parser = OptionParser()
parser.add_option("-s", "--source", action="store", type="string", dest="source", 
    help='Source of unzipped packages.\nE.g. /data/hcpdb/packages/unzip/')
parser.add_option("-t", "--target-devices", action="store", type="string", dest="device_list", 
    help='File containing list of destination drives\n(one per line), E.g. sda\nsdb\nsdc.')
parser.add_option("-l", "--subject-list", action="store", type="string", dest="subject_list", 
    help='File containing list of subjects to copy from source, used by rsync as --files-from option.')
(opts, args) = parser.parse_args()

if not (opts.source and opts.device_list):
    parser.print_help()
    sys.exit(-1)

## GLOBALS ##
start = time.time()
sub_count = 0
device_list = []
"""
#msg = "== Connectome-in-a-Box drive creation report for: \n" + \
#      "== Drive label " + opts.source + " on machine " + socket.gethostname() + '\n' + \
#      "== " + str(datetime.now()) + '\n'
"""
VERIFY_SCRIPT_DIR = '/usr/local/bin/clone_cinab'
PACKAGER_HOME = os.path.join(VERIFY_SCRIPT_DIR, 'download-packager')
############

def clone_worker(device):
    create_log(device)
    #partition(device)
    #rsync(device)
    verify(device)

def partition(sdx):
    device_label = 'HCP-Q1-Reproc'

    logger.info("\n* Formatting and partitioning drives")
    logger.info("== " + str(datetime.now()))
    
    print 'sh /usr/local/bin/clone_cinab/partition.sh ' + sdx + ' ' + device_label
    proc = sp.Popen(['sh', '/usr/local/bin/clone_cinab/partition.sh', sdx, device_label], stdout=sp.PIPE)
    log_helper(proc)


def rsync(sdx):
    logger.info("* Rsync process started for /dev/"+sdx)

    logger.info("\n* Cloning /dev/%s from source %s on %s" % (sdx, opts.source, socket.gethostname()))
    logger.info("== " + str(datetime.now()))
    logger.info(str(sub_count) + " subjects to rsync")

    if opts.subject_list:
        proc = sp.Popen(['rsync', '-avhr', '--relative', '--files-from='+opts.subject_list,
                         opts.source, '/media/'+sdx], stdout=sp.PIPE)
    else:
        proc = sp.Popen(['rsync', '-avh', opts.source, '/media/'+sdx], stdout=sp.PIPE)
        
    logger.info('== Launching Rsync:')
    #logger.info('sudo rsync -avhr --relative --files-from='+ opts.subject_list +' '+
    #        opts.source+' /dev/'+sdx)
    log_helper(proc)

    if proc.returncode > 0:
        logger.info("++ Something happened with rsync\nReturn code "+ proc.returncode)
        msg = "\n++ Rsync process failed."
        email(msg)
        exit(-1)
    else:
        logger.info('== Cloning process completed')
#        msg += "\nRsync process completed in "+ str(timedelta(seconds=time.time()-start))


def verify(sdx):
    verify_start = time.time()
    os.chdir(VERIFY_SCRIPT_DIR)

    logger.info('\n* Starting verification process --')
    logger.info('Start time - ' + str(datetime.now()))
    proc = sp.Popen([os.path.join(VERIFY_SCRIPT_DIR, 'PackageVerifier.sh'), \
                    '/media/'+sdx], stdout=sp.PIPE)
    log_helper(proc)

    if proc.returncode > 0:
        logger.info("++ Some packages failed verification\nSee details below")
#        msg += "\nVerification failed on one or more packages.\nSee log for details"
    else:
        logger.info("== Verification completed successfully")
#   	msg += "\nVerification completed successfully in "+ str(timedelta(seconds=time.time()-verify_start))


def email(message):
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    recipients = ['hilemanm@mir.wustl.edu']
    sender = 'mhilema@gmail.com'
    subject = 'CinaB Report: ' + datetime.strftime(datetime.today(), "%Y-%m-%d")
    headers = ["From: " + sender,"Subject: " + subject,"To: hilemanm@mir.wustl.edu"]
    headers = "\r\n".join(headers)
    session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    session.ehlo()
    session.starttls()
    session.ehlo
    session.login(sender, '8qar9wor')
    session.sendmail(sender, recipients, headers+"\r\n\r\n"+message)
    session.quit()


############################
##    Helper Functions    ##
############################

def count_subjects():

    if opts.subject_list:
        try:
            f = open(opts.subject_list)
        except:
            logger.error('== Could not open subject list file - ' + opts.subject_list)
            print "exception opening subject list file"

        global sub_count
        for line in f.readlines():
            sub_count += 1
    else:
        # count the numbered, top-level dirs on destination
        pass


def get_devices():
    try:
        f = open(opts.device_list)
    except:
        logger.error('== Could not open device list file - ' + opts.subject_list)
        print "exception opening device list file"

    global device_list
    for dev in f.readlines():
        device_list.append(dev.strip())

    if not device_list:
        print "device list is empty"
        exit(-1)


def create_log(sdx):
    global logger
    sp.call(['mkdir', '-p', '/usr/local/bin/clone_cinab/logs/'+str(datetime.now()).split()[0].strip('-')])
    logfile = '/usr/local/bin/clone_cinab/logs/'+str(datetime.now()).split()[0]+'/cinab-' + \
               sdx + '-' + socket.gethostname().split('.')[0]+'.log' 
    logger = logging.getLogger('clonecinab')
    handler = logging.FileHandler(logfile)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    print logfile


def log_helper(process):
    while True:
        line = process.stdout.readline()
        if not line:
            break
        line = line[0:-1] # get rid of extra newline char
        logger.info(line)


if __name__ == "__main__":
    get_devices()
    count_subjects()

    jobs = []
    for dev in device_list:
        p = mp.Process(name=dev, target=clone_worker, args=(dev,))
        jobs.append(p)
        p.start()
    
    total_time = str(timedelta(seconds=time.time()-start)).split('.')[0]
    
    """ need to wait until all processes complete
    msg = "Cloning process complete for the following drives:\n"
    for sdx in device_list:
        msg += "/media/"+sdx+"\n"
    msg += "\nTotal time: " + total_time
    email(msg)

    logger.info("== Process completed - " + str(datetime.now()))
    logger.info("== Total time - " + total_time)
    """
