#!/bin/bash

for i in {48..95}; do
    if mountpoint -q /media/bay$i; then
      echo "Launching verify-md5.py on bay$i" 
      nohup python verify-md5.py /media/bay$i /opt/cinabox/logs/verify/bay$i-verify.log &
    else
      echo "No drive mounted at /media/bay$i"
    fi
done
