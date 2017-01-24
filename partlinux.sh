#!/bin/bash

# unmount and remove existing partition, assumes only 1 existing
#umount /dev/${1}1
umount /root/disks/part/${1}
#parted /dev/$1 --script rm 1
parted /root/disks/dev/$1 --script rm 1
sleep 3

# create gpt partition map, align optimal
parted -a optimal /root/disks/dev/$1 --script -- mklabel gpt
sleep 3

# create primary partition and format
#parted -a optimal /dev/$1 --script -- mkpart primary 1 100%
parted -a optimal /root/disks/dev/${1} --script -- mkpart primary 1 100%
sleep 3
#mkfs -t ext4 -L "${2}" /dev/${1}1
mkfs -t ext4 -L "${2}" /root/disks/part/${1}
sleep 3

# create mount dir based on device letter and mount
mkdir -p /media/${1}
chmod 755 /media/${1}
mount -t ext4 /root/disks/part/${1} /media/$1

# delete lost+found folder
rmdir /media/$1/lost+found/
