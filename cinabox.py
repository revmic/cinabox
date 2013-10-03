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
from email.mime.text import MIMEText
from datetime import datetime, timedelta

## TO-DO
#  * Log elapsed times for each device
#  * Verify targets are same size as source (if cloning from disk)
#  * Pull email recipient list out as config file

## OPTION PARSER ##
parser = OptionParser(usage='\n(Multiple destinations from local source with device label):'+
                            '\npython cinabox.py -s /media/Q1-Source -t devices.list -l HCP-Q1')
parser.add_option("-s", "--source", action="store", type="string", dest="source", 
    help='Source of unzipped packages.\nE.g. /data/hcpdb/packages/unzip/')
parser.add_option("-t", "--targets", action="store", type="string", dest="targets", 
    help='File containing list of target drives\n(one per line), E.g. sda\nsdb\nsdc.')
parser.add_option("-S", "--subject-list", action="store", type="string", dest="subject_list", 
    help='File containing list of subjects to copy from source.\nUsed by rsync as --files-from option.')
parser.add_option("-l", "--device-label", action="store", type="string", dest="device_label",
    help='Label given to all target devices.')
parser.add_option("-n", "--notify", action="store_true", dest="notify", default=False,
    help='Turns on email notification when used.')
parser.add_option("-u", "--update", action="store_true", dest="update", default=False, 
    help='Update existing drive instead of rewriting.')
parser.add_option("-v", "--verify", action="store_true", dest="verify", default=False,
    help='Verify only. Useful for drive recycling.')
(opts, args) = parser.parse_args()

## HANDLE OPTIONS ##
if not ((opts.source or opts.verify) and opts.targets):
    parser.print_help()
    sys.exit(-1)

if not (opts.device_label or opts.verify):
    response = ''
    while response is not 'y' or response is not 'n':
        response = raw_input("No target device label provided. "+ \
                             "\'HCP-Cinab\' will be used.\nContinue? (y/n): ")
        if response is 'y':
            break
        elif response is 'n':
            exit(0)
        else:
            print "Not a proper response. Type y/n."

## GLOBALS ##
start = time.time()
startdate = str(datetime.now()).split('.')[0]
sub_count = 0
targets = []
SCRIPTDIR = os.getcwd()
LOGDIR = os.path.join(SCRIPTDIR, 'logs')
VERIFY_SCRIPT_DIR = os.getcwd()
PACKAGER_HOME = os.path.join(VERIFY_SCRIPT_DIR, 'download-packager')
############

def create_log(drive):
    global logger
    datedir = str(datetime.now()).split()[0].replace('-', '')
    sp.call(['mkdir', '-p', os.path.join(LOGDIR, datedir)])
    logfile = os.path.join(LOGDIR, datedir +'/cinab-' + drive + '-' + \
                           socket.gethostname().split('.')[0]+'.log')
    logger = logging.getLogger('cinab')
    handler = logging.FileHandler(logfile)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

def partition(drive):
    if not opts.device_label:
        opts.device_label = 'HCP-Cinab'

    logger.info("\n* Formatting and partitioning drives")
    logger.info("== " + str(datetime.now()))
    
    if 'linux' in sys.platform:
        print 'sh partlinux.sh ' + drive + ' ' + opts.device_label
        proc = sp.Popen(['sh', 'partlinux.sh', drive, opts.device_label], stdout=sp.PIPE)
    elif 'darwin' in sys.platform:
        print 'Running on Mac OS'
        # proc = sp.Popen(['sh', '/usr/local/bin/clone_cinab/partmac.sh', drive, device_label], stdout=sp.PIPE)
        exit(-1)
    elif 'win' in sys.platform:
        print 'Running on Win'
        # proc = sp.Popen(['sh', '/usr/local/bin/clone_cinab/partwin.bin', drive, device_label], stdout=sp.PIPE)
        exit(-1)
    else:
        print 'Unknown operating system: ' + sys.platform
        exit(-1)
        
    log_helper(proc)
    logger.info('\n\n')

def rsync(drive):
    logger.info("* Rsync process started for "+drive)

    logger.info("\n* Cloning /dev/%s from source %s on %s" % (drive, opts.source, socket.gethostname()))
    logger.info("== " + str(datetime.now()))
    logger.info(str(sub_count) + " subjects to rsync")

    if 'linux' in sys.platform or 'darwin' in sys.platform:
        # If the source directory is pulling from hcpdb/packages,
        # change group of executing user to hcp_open
        if 'hcpdb' in opts.source:
            os.setgid(60026)
        if opts.subject_list:
            proc = sp.Popen(['rsync', '-avhr', '--relative', '--files-from='+opts.subject_list, 
                              opts.source, '/media/'+drive], stdout=sp.PIPE)
        else:
            proc = sp.Popen(['rsync', '-avh', opts.source, '/media/'+drive], stdout=sp.PIPE)
    elif 'win' in sys.platform:
        print "WINDOWS"
        # proc = sp.Popen(Some windows copy process)
    else:
        'Unknown operating system: ' + sys.platform
        exit(-1)
        
    logger.info('== Launching Rsync:')
    #logger.info('sudo rsync -avhr --relative --files-from='+ opts.subject_list +' '+
    #        opts.source+' /dev/'+drive)
    log_helper(proc)

    print "Rsync return code: " + str(proc.returncode)
    if proc.returncode > 0:
        logger.info("++ Something happened with rsync\nReturn code "+ proc.returncode)
        msg = "\n++ Rsync process failed."
        #email(msg)
        exit(-1)
    else:
        logger.info('== Rsync subprocess completed')

    # Set permissions
    # chown -R root:root sda
    # chmod -R 664 sda
    # chmod -R +X sda
    # find sda -name "*.sh" | xargs chmod +x

def verify(drive):
    verify_start = time.time()
    os.chdir(VERIFY_SCRIPT_DIR)

    logger.info('\n* Starting verification process --')
    logger.info('Start time - ' + str(datetime.now()))
    proc = sp.Popen(['./PackageVerifier.sh', '/media/'+drive], stdout=sp.PIPE)
    log_helper(proc)

    print "PackageVerifier return code: " + str(proc.returncode)
    if proc.returncode > 0:
        logger.info("++ Some packages failed verification\nSee details below")
    else:
        logger.info("== Verification process complete")

def email(subject, recipients, sender, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)

    session = smtplib.SMTP('mail.nrg.wustl.edu')
    session.sendmail(sender, recipients, msg.as_string())
    session.quit()


############################
##    Helper Functions    ##
############################

def count_subjects():
    global sub_count

    if opts.subject_list:
        try:
            f = open(opts.subject_list)
        except:
            print "Exception opening subject list file. Make sure it exists and you have permission."
            exit(-1)

        for line in f.readlines():
            sub_count += 1
    else:
        # Count the number of directories on the top level of source disk
        sub_count = os.listdir(opts.source).__len__()
        
def get_devices():
    try:
        f = open(opts.targets)
    except:
        print "Exception opening device list file. Make sure it exists."
        exit(-1)

    global targets
    for dev in f.readlines():
        targets.append(dev.strip())

    if not targets:
        print "device list is empty"
        exit(-1)

def log_helper(process):
    while True:
        line = process.stdout.readline()
        if not line:
            break
        line = line[0:-1] # get rid of extra newline char
        logger.info(line)

def build_message(total_time):
    msg = "Cloning process complete for "+ str(targets.__len__())+" "+ \
          opts.device_label + " drives on " + sys.platform + " platform."
    msg += "\n\nStarted on: "+ startdate
    msg += "\nCompleted: "+ str(datetime.now()).split('.')[0]
    msg += "\nElapsed: " + total_time
    msg += "\n\nCheck the logs for details at "+ LOGDIR  + " on "+socket.gethostname()
    return msg

##############################

def clone_worker(device):
    create_log(device)
    if opts.verify:
        print "VERIFY only"
        verify(device)
    else:
        if opts.update:
            print "UPDATING the targets"
        else:
            partition(device)
        rsync(device)
        verify(device)

if __name__ == "__main__":
    get_devices()
    count_subjects()
    
    processes = []
    for dev in targets:
        p = mp.Process(name=dev, target=clone_worker, args=(dev,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    total_time = str(timedelta(seconds=time.time()-start)).split('.')[0]

    if opts.notify:
        message = build_message(total_time)
        recipients = ['hilemanm@mir.wustl.edu', 'moore.c@wustl.edu', 
                      'clere@mir.wustl.edu', 'hortonw@mir.wustl.edu']
        sender = 'cinab@nrg.wustl.edu'
        subject = 'CinaB Report: ' + datetime.strftime(datetime.today(), "%Y-%m-%d")
        email(subject, recipients, sender, message)

    print "Elapsed time: " + str(total_time)

    #logger.info("== Process completed - " + str(datetime.now()))
    #logger.info("== Total time - " + total_time)

