#!/usr/bin/env python

from datetime import datetime
import hashlib
import glob
import sys
import os

def md5(fname):
    hash = hashlib.md5()
    with open(fname) as f:
        for chunk in iter(lambda: f.read(4096), ""):
            hash.update(chunk)
    return hash.hexdigest()

def verify_md5(directory, logfile):
    filecount = 0
    totalsize = 0
    errors = 0
    started = datetime.now()

    with open(logfile, 'w') as log:
        log.write("Started verification on {} at {}\n\n".format(
            directory, str(started)))

    for root, dirs, files in os.walk(directory):
        for f in files:
            if not f.endswith('.zip'):
                continue

            filecount += 1
            file_path = os.path.join(root, f)
            # file_md5 = hashlib.md5(open(file_path).read()).hexdigest()
            file_md5 = md5(file_path)
            totalsize += os.path.getsize(file_path)

            try:
                manifest_md5 = open(file_path + '.md5').read().split()[0]
            except IOError as e:
                with open(logfile, 'a') as log:
                    log.write('IOERROR -- Attempting to open {}\n'.format(
                        file_path))
                print e

            # print file_md5
            # print manifest_md5
        
            if file_md5 == manifest_md5:
                print 'OK -- ' + file_path
            else:
                print 'ERROR -- ' + file_path
                errors += 1
                with open(logfile, 'a') as log:
                    log.write("{} failed md5 verification\n".format(
                        file_path))

    finished = datetime.now() - started

    with open(logfile, 'a') as log:
        log.write("Finished verification at {} -- {} elapsed\n".format(
            str(datetime.now()), str(finished)))
        log.write("{} errors found for {} files in {} -- {} bytes\n\n".format(
            errors, filecount, directory, totalsize))
    
    return filecount, totalsize, errors


if __name__ == "__main__":
    try:
        directory = sys.argv[1]
    except:
        print "You must provide a directory to check md5sums"
        sys.exit()

    try:
        logfile = sys.argv[2]
    except:
        logfile = 'verify-md5.log'

    files, size, errors = verify_md5(directory, logfile)

    print "Found {} errors in {} -- {} files, {} bytes".format(
        errors, directory, files, size)
    print "Check {} for more info.".format(
        logfile)
