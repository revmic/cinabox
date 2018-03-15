#!/bin/bash
set -x

nohup python cinabox.py -s /media/1200cinab/disk1/  -t 0-1 -l S1200-5 -n &
sleep 20;
nohup python cinabox.py -s /media/1200cinab/disk2/  -t 2-2 -l S1200-6 -n &
sleep 20;
nohup python cinabox.py -s /media/1200cinab/disk3/  -t 3-3 -l S1200-7 -n &
sleep 20;
nohup python cinabox.py -s /media/1200cinab/disk4/  -t 4-5 -l S1200-10 -n &
#sleep 20;
#nohup python cinabox.py -s /media/1200cinab/disk5/  -t 9-10 -l S1200-5 -n &
#sleep 20;
#nohup python cinabox.py -s /media/1200cinab/disk6/  -t 11-12 -l S1200-6 -n &
#sleep 20;
#nohup python cinabox.py -s /media/1200cinab/disk7/  -t 13-14 -l S1200-7 -n &
#sleep 20;
#nohup python cinabox.py -s /media/1200cinab/disk8/  -t 15-17 -l S1200-8 -n &
#sleep 20;
#nohup python cinabox.py -s /media/1200cinab/disk9/  -t 18-20 -l S1200-9 -n &
#sleep 20;
#nohup python cinabox.py -s /media/1200cinab/disk10/ -t 21-22 -l S1200-10 -n &
#sleep 20;
#nohup python cinabox.py -s /media/1200cinab/disk11/ -t 23-25 -l S1200-11 -n &
#sleep 20;
#nohup python cinabox.py -s /media/1200cinab/disk12/ -t 26-31 -l S1200-12 -n &

