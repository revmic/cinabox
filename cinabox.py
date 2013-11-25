#!/usr/bin/python
import os
import sys
import time
import envoy
import socket
import logging
import smtplib
import subprocess as sp
import multiprocessing as mp
from optparse import OptionParser
from email.mime.text import MIMEText
from datetime import datetime, timedelta

## TODO
# * Log elapsed times for each device
# * Pull email recipient list out as config file
# * Verification that all drives passed at end:
#   - tail cinab-sd* | grep -i error

## OPTION PARSER ##
parser = OptionParser(usage='\n(Multiple destinations from local source with device label):'+
                            '\npython cinabox.py -s /media/Q1-Source -t devices.list -l HCP-Q1'+
                            '\n(Source drive creation from hcpdb/packages using subject list):'+
                            '\npython cinabox.py -s /data/hcpdb/packages/unzip -S Q1.txt -t devices.list -l HCP-SRC')
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
if not (opts.targets and (opts.source or opts.verify)):
    parser.print_help()
    sys.exit(-1)

if not (opts.device_label or opts.verify or opts.update):
    response = ''
    while response is not 'y' or response is not 'n':
        response = raw_input("No target device label provided. "+ \
                             "\'HCP-Cinab\' will be used.\nContinue? (y/n): ")
        if response is 'y': break
        elif response is 'n': exit(0)
        else: print "Not a proper response. Type y/n."

## GLOBALS ##
starttime = time.time()
startdate = str(datetime.now()).split('.')[0]
sub_count = 0
target_devs = []
SCRIPTDIR = os.getcwd()
LOGDIR = os.path.join(SCRIPTDIR, 'logs')
VERIFY_SCRIPT_DIR = os.getcwd()
PACKAGER_HOME = os.path.join(VERIFY_SCRIPT_DIR, 'download-packager')
############

def create_log(drive):
    global logger
    datedir = str(datetime.now()).split()[0].replace('-', '')
    sp.call(['mkdir', '-p', os.path.join(LOGDIR, datedir)])
    logfile = os.path.join(LOGDIR, datedir, 'cinab-' + drive.replace('/','-') + '-' + \
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
    print "Partitioning " + drive
    
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
    logger.info('\n')

def rsync(drive):
    print "Starting rsync on /media/" + drive
    logger.info("\n== Cloning %s from source %s on %s" % (drive, opts.source, socket.gethostname()))
    logger.info(str(datetime.now()))
    logger.info(str(sub_count) + " subjects to rsync")

    if 'linux' in sys.platform or 'darwin' in sys.platform:
        # If the source directory is pulling from hcpdb/packages,
        # change group ID of subprocess to hcp_open
        if 'hcpdb' in opts.source:
            os.setgid(60026)

        if opts.subject_list:
            command = ['rsync', '-avhr', '--relative', '--files-from='+opts.subject_list, opts.source, '/media/'+drive]
        else:
            command = ['rsync', '-avh', opts.source, '/media/'+drive]
        proc = sp.Popen(command, stdout=sp.PIPE)

    elif 'win' in sys.platform:
        print "WINDOWS"
        # proc = sp.Popen(Some windows copy process)
    else:
        'Unknown operating system: ' + sys.platform
        exit(-1)
        
    logger.info(command)
    log_helper(proc)

    print "Rsync return code: " + str(proc.returncode)
    if proc.returncode > 0:
        logger.error("++ Something happened with rsync\nReturn code "+ proc.returncode)
        msg = "\n++ Rsync process failed."
        #email(msg)
        exit(-1)
    else:
        logger.info('== Rsync subprocess completed')

def mount(device):
    """
    Needed for updating or verifying a drive since it isn't mounted by partitioning subprocess
    """
    if 'linux' in sys.platform:
        mount_point = '/media/'+device

    if os.path.ismount(mount_point):
        print device + " already mounted"
        return

    print "Mounting /dev/" + device + " as /media/" + device
    if 'linux' in sys.platform:
        command = ['mount', '/dev/'+device+'1', device]
        proc = sp.Popen(command)
        print "mount return code: " + str(proc.returncode)
    else:
        print "Cannot MOUNT device " + device + ". Unknown OS: " + sys.platform
        sys.exit(-1)
    
def set_permissions(drive):
    if 'linux' in sys.platform:
        p = envoy.run('chown -R root:root /media/'+drive) 
        p = envoy.run('chmod -R 664 /media/'+drive)
        p = envoy.run('chmod -R +X /media/'+drive)
        p = envoy.run('find /media/'+drive+ ' -name "*.sh" | xargs chmod +x')
    else:
        print "Cannot set PERMISSIONS for " + device + ". Unknown OS: " + sys.platform

def verify(drive):
    verify_start = time.time()
    os.chdir(VERIFY_SCRIPT_DIR)

    logger.info('\n'+str(datetime.now()))
    proc = sp.Popen(['./PackageVerifier.sh', '/media/'+drive], stdout=sp.PIPE)
    log_helper(proc)
    # print "PackageVerifier return code: " + str(proc.returncode)

    if not opts.source:
        print "No source disk to verify against"        
    # Only verify disk size if created from another disk (not hcpdb)
    elif 'media' in opts.source and not (opts.subject_list or opts.verify):
        source_size = get_size(opts.source)
        target_size = get_size(drive)

        print "Verifying size of devices."
        logger.info('\n* Verifying size of devices.')
        logger.info("Source size: " + str(source_size))
        logger.info("Target size: " + str(target_size))

        # Check that SOURCE is same size as TARGET within 2 bytes.
        if source_size < target_size-2 or source_size > target_size+2:
            logger.warning("Source differs from target ("+drive+") by more than 2 bytes.")
        else:
            logger.info("Source ("+opts.source+") and target ("+drive+") are the same size.")

    if proc.returncode > 0:
        logger.warning("++ Some packages failed verification\nSee details below")
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
    """
    Handles either a file with a list of devices or a single dir location
    """
    if os.path.isfile(opts.targets):
        try:
            f = open(opts.targets)
        except:
            print "Exception opening device list file. Make sure it exists."
            exit(-1)
    
        global target_devs
        for dev in f.readlines():
            target_devs.append(dev.strip())
    
        if not target_devs:
            print "device list is empty"
            exit(-1)
    elif os.path.isdir(opts.targets):
        target_devs.append(opts.targets.split('/')[-1])
    else:
        print "Couldn't figure out the target option."
        print "It doesn't seem to be either a list or a directory."
        exit(-1)

def get_size(mount):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(mount):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def log_helper(process):
    while True:
        line = process.stdout.readline()
        if not line:
            break
        line = line[0:-1] # get rid of extra newline char
        logger.info(line)

def build_message(total_time):
    msg = "Cloning process complete for "+ str(target_devs.__len__())+" "+ \
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
        print "Package VERIFY only"
        mount(device)
        verify(device)
    else:
        if opts.update:
            print "UPDATING device " + device
            mount(device)
        else:
            partition(device)
        rsync(device)
        set_permissions(device)
        verify(device)

if __name__ == "__main__":
    get_devices()
    if not opts.verify:
        count_subjects()
    
    processes = []
    for dev in target_devs:
        p = mp.Process(name=dev, target=clone_worker, args=(dev,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    total_time = str(timedelta(seconds=time.time()-starttime)).split('.')[0]

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

