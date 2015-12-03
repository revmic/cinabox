#!/bin/bash

# unmount and remove existing partition, assumes only 1 existing
umount /dev/${1}1
parted /dev/$1 --script rm 1

# create gpt partition map, align optimal
parted -a optimal /dev/$1 --script -- mklabel gpt

# create primary partition and format
parted -a optimal /dev/$1 --script -- mkpart primary 1 100%
mkfs -t ext2 -L "${2}" /dev/${1}1

# create mount dir based on device letter and mount
mkdir -p /media/${1}
chmod 755 /media/${1}
mount -t ext2 /dev/${1}1 /media/$1

# delete lost+found folder
rmdir /media/$1/lost+found/
