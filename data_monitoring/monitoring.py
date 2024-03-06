#!/usr/bin/python

from ROOT import *
import json
import os.path
import time
import socket
import sys
import time
import logging
import subprocess
import glob
import shutil
import os

### some global settings
WORKDIR = '/home/jpet/monitoring/j-pet-online-monitoring/data_monitoring/'
ROOTFILES_LOCATION = '/home/jpet/monitoring/j-pet-online-monitoring/data_monitoring/web/rootfiles/'
DATA_MOUNTPOINT = '/data/DAQ/'

###
# Number of events (time windows) to be processed 
###
NUMBER_EVENTS = 100000000 # absurdly large number to ensure the whole file is analyzed
#NUMBER_EVENTS = 10000
###

### Create a lock to prevent multiple instances running at the same time
def get_lock(process_name):
    # Without holding a reference to our socket somewhere it gets garbage
    # collected when the function exits
    get_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        get_lock._lock_socket.bind('\0' + process_name)
        return True
    except socket.error:
        return False

### main
# setup a logger
logging.basicConfig(filename='monitoring.log',level=logging.DEBUG,
                    format = '%(asctime)s - %(levelname)s: %(message)s',
                    datefmt = '%m/%d/%Y %I:%M:%S %p')

# process given HLD file path
os.chdir(WORKDIR)
input_hld_file_path = sys.argv[1]

print(input_hld_file_path)

hld_filename = os.path.split(input_hld_file_path)[1]
hld_path = os.path.split(input_hld_file_path)[0]

# log first information
logging.info('Received monitoring request for file ' + hld_filename)

if hld_filename.endswith('.hld'):
    core_filename = hld_filename[:-4]
else:
    logging.critical('The provided filename does not end with a .hld extension')
    sys.exit(2)

# try to obtain a process lock and exit if another instance was found
# this is signalled wit -3 return code
if not get_lock('jpet_jlab_monitoring'):
    logging.critical('Another instance of J-Lab monitoring reconstruction is already running. Skipping reconstruction of ' + hld_filename + '.')
    sys.exit(3)

# log start of processing
logging.info('Starting reconstruction of ' + str(NUMBER_EVENTS) + ' time windows for the file ' + hld_filename + '.')

# link or copy the file to the working directory
if not os.path.isfile(hld_filename):
    try:
        shutil.copy(input_hld_file_path, './'+hld_filename)
    except shutil.Error as e:
        logging.critical('Error copying file '+hld_filename + ': '+str(e))
        sys.exit(4);
    except IOError as e:
        logging.critical('Error copying file '+hld_filename + ': '+e.strerror)
        sys.exit(4);

# os.system("xz -d dabc*xz")
# hld_filename = hld_filename.rsplit('.',1)[0]

# execute the reconstruction for a given file
start_time = time.time()
try:
    FNULL = open(os.devnull, 'w')
    subprocess.check_call([
       "/home/jpet/monitoring/examples-build/ModularDetectorAnalysis/ModularDetectorAnalysis.x",
        "-t", "hld",
        "-k", "modular",
        "-u", str(WORKDIR) + "configs/up.24.01.json",
        "-l", str(WORKDIR) + "configs/modular_setup_clinical_fixed_ds.json",
        "-i", str(38),
        "-f", hld_filename,
        "-r", str(0), str(NUMBER_EVENTS),
        "-d"
    ],
    stderr=subprocess.STDOUT,
    stdout=FNULL,
    close_fds=True
    )
    
except subprocess.CalledProcessError as e:
    logging.critical('Reconstruction process crashed for ' + hld_filename + '.')
    logging.debug('Command: ' + '_'.join(e.cmd))
    sys.exit(5)

end_time = time.time()
    
# log end of processing
logging.info('Reconstruction ended successfully for the file ' + hld_filename + '.')
logging.info("Reconstruction took {} s.".format(end_time-start_time))

# remove the symlink to HLD file
os.unlink(hld_filename)

out_filename = time.strftime("%Y_%m_%d_%H_%M") + '_' + core_filename + ".root"

filename = core_filename + '.' + 'cat.evt.root'

# move the created rootfile to the final location
os.rename(filename, ROOTFILES_LOCATION+'/'+out_filename)

# add the created rootfile to the list
with open('web/files.json', mode='r') as file_list_json:
    file_list = json.load(file_list_json)

file_list["files"].append(out_filename)

with open('web/files.json', mode='w') as file_list_json:
    json.dump(file_list, file_list_json)

# clean up the created ROOT files
for file in glob.glob(core_filename+".*.root"):
    os.remove(file)

# just in case, remove any remaining binary files
for file in glob.glob("./*.root"):
    os.remove(file)
for file in glob.glob("./*.hld"):
    os.remove(file)

logging.info('Monitoring job completed for the file ' + hld_filename + '.')
