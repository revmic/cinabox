#!/bin/bash

# Monitor write progress: -w
# Monitor drive temperature: -t

progress () {
    echo "Watching write progress. Control-C to exit ..."
    sleep 2
    watch -n 0.1 'df | egrep "bay|src" | sort -k6'
}

temp () {
    echo "Checking hdd temperatures ..."
    for bay in /root/disks/dev/* ; do
        if [ -e $bay ] ; then
            hddtemp $bay
        fi
    done
}

while getopts ":tp" opt; do
    case $opt in
        p)
            progress
            ;;
        t)
            temp
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            echo "-p for write progress"
            echo "-t for hdd temperatures"
            exit 1
            ;;
        #:)
        #    echo "Option -$OPTARG requires a partition substring to filter." >&2
        #    exit 1
        #    ;;
    esac
done
