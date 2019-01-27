import glob
import os
import os.path
from operator import itemgetter
import time
import subprocess

def getMostRecentFolder(path, folder_name_pattern):
    list = [(os.path.getmtime(entry), entry) for entry in glob.glob(path + '/'+folder_name_pattern) if os.path.isdir(entry)]
    return max(list,key=itemgetter(0))

def getMostRecentFile(path):
    list = [(os.path.getmtime(entry), entry) for entry in glob.glob(path + '/*.hld') if os.path.isfile(entry)]
    return max(list,key=itemgetter(0))

# def getFreeSpace(path):
#     ouput = subprocess.check_output(['df', '-h '+str(path)])
#     print output

#t = getMostRecentFile(getMostRecentFolder('/data/DAQ/')[1])[0]
#print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))

#getFreeSpace('/data/DAQ/')
