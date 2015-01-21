cinabox
=======

Connectome-in-a-Box Drive Creation

Run 'python cinabox.py --help' for options and usage info.

Usage: 

(Multiple destinations from local source with device label):

python cinabox.py -s /media/HCP-SOURCE -t devices.list -l HCP-S500

(Source drive creation from hcpdb/packages using subject list):

python cinabox.py -s /data/hcpdb/packages/unzip -S Q1.txt -t devices.list -l HCP-SOURCE

Options:

  -h, --help        show this help message and exit

  -s SOURCE, --source=SOURCE

                        Source of unzipped packages. E.g.

                        /data/hcpdb/packages/unzip/

  -t TARGETS, --targets=TARGETS

                        File containing list of target drives (one per line),

                        E.g. sda 

                               sdb 

                               sdc.

  -S SUBJECT_LIST, --subject-list=SUBJECT_LIST

                        File containing list of subjects to copy from source.

                        Used by rsync as --files-from option.

  -l DEVICE_LABEL, --device-label=DEVICE_LABEL

                        Label given to all target devices.

  -n, --notify          Turns on email notification when used.

  -u, --update        Update existing drive instead of rewriting.

  -v, --verify          Verify only. Useful for drive recycling.
