#!/bin/bash

ROOT=/root/disks/part

get_label () {
    label=`lsblk -o LABEL $1 | grep S`
    
    # Check if disk already mounted under this label and increment if so
    count=0
    while mount | grep ${label}_${count} >> /dev/null; do
        ((count=$count+1))
    done

    echo ${label}_${count}
}

for partition in $ROOT/* ; do
    if [ -e $partition ]; then

        # Get the partition label or bay depending on passed param
        if [ "$@" = "-l" ]; then
            mount_point=$(get_label $partition)
        elif [ "$@" = "-b" ]; then
            mount_point=`basename $partition`
        else
            echo "Use -l to mount using label or -b for bay number."
            exit 1
        fi
        
        # Make directory and mount in /media
        mkdir -p /media/$mount_point
        echo "mounting $partition to /media/$mount_point ..."
        mount $partition /media/$mount_point
        sleep 2
    fi
done


