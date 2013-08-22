#!/usr/bin/python
import os
import sys
import time
import errno
#import setup
import socket
import logging
import smtplib
import subprocess as sp
import multiprocessing as mp
from optparse import OptionParser
from datetime import datetime, timedelta

"""
## devices.list contents ##
sdb
sdc
sdd
"""
## TO-DO
#    Log elapsed times

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
parser.add_option("-u", "--update", action="store_true", dest="update", default=False, 
    help='Update existing drive instead of rewriting.')
parser.add_option("-v", "--verify", action="store_true", dest="verify", default=False,
    help='Verify only. Useful for drive recycling.')
(opts, args) = parser.parse_args()

## HANDLE PROVIDED OPTIONS ##
if not (opts.source and opts.targets):
    parser.print_help()
    sys.exit(-1)

if not opts.device_label:
    response = ''
    while response is not 'y' or response is not 'n':
        response = raw_input("No target device label provided. \'HCP-Cinab\' will be used.\nContinue? (y/n): ")
        if response is 'y':
            break
        elif response is 'n':
            exit(0)
        else:
            print "Not a proper response. Type y/n."

## GLOBALS ##
start = time.time()
startdate = str(datetime.now()).split('.')[0]
logdir = '/usr/local/bin/clone_cinab/logs/'
sub_count = 0
targets = []
SCRIPTDIR = os.getcwd()
LOGDIR = os.path.join(SCRIPTDIR, 'logs')
"""
#msg = "== Connectome-in-a-Box drive creation report for: \n" + \
#      "== Drive label " + opts.source + " on machine " + socket.gethostname() + '\n' + \
#      "== " + str(datetime.now()) + '\n'
"""
VERIFY_SCRIPT_DIR = '/data/hcpdb/ftp/staging.mdh/OpenAccess/packaging-scripts/PackageQ2/'
PACKAGER_HOME = os.path.join(VERIFY_SCRIPT_DIR, 'download-packager')
############

def create_log(drive):
    global logger
    sp.call(['mkdir', '-p', LOGDIR + str(datetime.now()).split()[0].replace('-', '')])
    logfile = os.path.join(LOGDIR, str(datetime.now()).split()[0]+'/cinab-' + \
               drive + '-' + socket.gethostname().split('.')[0]+'.log')
    logger = logging.getLogger('cinab')
    handler = logging.FileHandler(logfile)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    print logfile

def partition(drive):
    if not opts.device_label:
        opts.device_label = 'HCP-Cinab'

    logger.info("\n* Formatting and partitioning drives")
    logger.info("== " + str(datetime.now()))
    
    if 'linux' in sys.platform:
        print 'sh /usr/local/bin/clone_cinab/partlinux.sh ' + drive + ' ' + opts.device_label
        proc = sp.Popen(['sh', '/usr/local/bin/clone_cinab/partlinux.sh', 
                          drive, opts.device_label], stdout=sp.PIPE)
    elif 'darwin' in sys.platform:
        print 'Running on Mac OS'
        # proc = sp.Popen(['sh', '/usr/local/bin/clone_cinab/partmac.sh', drive, device_label], stdout=sp.PIPE)
        exit(-1)
    elif 'win' in sys.platform:
        print 'Running on Win'
        # proc = sp.Popen(['sh', '/usr/local/bin/clone_cinab/partwin.bin', drive, device_label], stdout=sp.PIPE)
        exit(-1)
    else:
        print 'Unknown operating system'
        exit(-1)
        
    log_helper(proc)
    logger.info('\n\n')

def rsync(drive):
    logger.info("* Rsync process started for "+drive)

    logger.info("\n* Cloning /dev/%s from source %s on %s" % (drive, opts.source, socket.gethostname()))
    logger.info("== " + str(datetime.now()))
    logger.info(str(sub_count) + " subjects to rsync")

    if 'linux' in sys.platform or 'darwin' in sys.platform:        
        if opts.subject_list:
            proc = sp.Popen(['rsync', '-avhr', '--relative', '--files-from='+opts.subject_list,
                             opts.source, '/media/'+drive], stdout=sp.PIPE)
        else:
            proc = sp.Popen(['rsync', '-avh', opts.source, '/media/'+drive], stdout=sp.PIPE)
    elif 'win' in sys.platform:
        print "WINDOWS"
        # proc = sp.Popen(Some windows copy process)
    else:
        'Unknown operating system'
        exit(-1)
        
    logger.info('== Launching Rsync:')
    #logger.info('sudo rsync -avhr --relative --files-from='+ opts.subject_list +' '+
    #        opts.source+' /dev/'+drive)
    log_helper(proc)

    print "Rsync return code: " + str(proc.returncode)
    if proc.returncode > 0:
        logger.info("++ Something happened with rsync\nReturn code "+ proc.returncode)
        msg = "\n++ Rsync process failed."
        email(msg)
        exit(-1)
    else:
        logger.info('== Rsync subprocess completed\n\n')


def verify(drive):
    verify_start = time.time()
    os.chdir(VERIFY_SCRIPT_DIR)

    logger.info('\n* Starting verification process --')
    logger.info('Start time - ' + str(datetime.now()))
    proc = sp.Popen(['/data/hcpdb/ftp/staging.mdh/OpenAccess/packaging-scripts/PackageQ2/PackageVerifier.sh', \
                     '/media/'+drive], stdout=sp.PIPE)
    log_helper(proc)

    print "PackageVerifier return code: " + str(proc.returncode)
    if proc.returncode > 0:
        logger.info("++ Some packages failed verification\nSee details below")
    else:
        logger.info("== Verification completed successfully")


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
            print "exception opening subject list file"

        global sub_count
        for line in f.readlines():
            sub_count += 1
    else:
        # count the numbered, top-level dirs on destination
        pass


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
    msg = "Cloning process complete for "+ str(targets.__len__())+ \
          " drives on " + sys.platform + " platform."
    msg += "\n\nStarted on: "+ startdate
    msg += "\nCompleted: "+ str(datetime.now()).split('.')[0]
    msg += "\nElapsed: " + total_time
    msg += "\n\nCheck the logs for details at "+ logdir + " on "+socket.gethostname()
    return msg

##############################


def clone_worker(device):
    #create_log(device)
    if opts.verify:
        print "VERIFY only"
        #verify(device)
    else:
        if not opts.update:
            print "UPDATING the targets"
            #partition(device)
        #rsync(device)
        #verify(device)
        print "do work on " + device
        time.sleep(3)

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
    m = build_message(total_time)
    email(m)
    print "Elapsed time: " + str(total_time)

    #logger.info("== Process completed - " + str(datetime.now()))
    #logger.info("== Total time - " + total_time)

