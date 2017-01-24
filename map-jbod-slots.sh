#!/bin/sh

# Based on
# http://en.community.dell.com/techcenter/b/techcenter/archive/2013/08/07/determining-drive-slot-location-on-linux-for-lsi-9207-sas-controllers

pci_name="pci-0000:02:00.0-sas"

for name in /sys/block/* ; do

    dev_path=$(readlink -f $name)

    while [ $dev_path != "/" ] ; do
        dev_path=$(dirname $dev_path)
        end_device=$(basename $dev_path)
  
        if [ -e $dev_path/sas_device/$end_device/bay_identifier ] ; then
            bay=$(cat $dev_path/sas_device/$end_device/bay_identifier)
            sas_address=$(cat $dev_path/sas_device/$end_device/sas_address)
            ln -s /dev/disk/by-path/$pci_name-$sas_address-lun-0 /root/disks/dev/bay$bay
            ln -s /dev/disk/by-path/$pci_name-$sas_address-lun-0-part1 /root/disks/part/bay$bay
            break
        fi
    done

done
