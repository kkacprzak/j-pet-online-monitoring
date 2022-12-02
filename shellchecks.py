import glob
import os
import os.path
from operator import itemgetter
import time
import subprocess

class NoFilesError(Exception):
    pass

def getMostRecentFolder(path, folder_name_pattern):
    list = [(os.path.getmtime(entry), entry) for entry in glob.glob(path + '/'+folder_name_pattern) if os.path.isdir(entry)]
    return max(list,key=itemgetter(0))[1]

def listHLDfiles(path):
    file_list = [(os.path.getmtime(entry), entry) for entry in glob.glob(path + '/*.hld') if os.path.isfile(entry)]
    if len(file_list) == 0:
        raise NoFilesError('Zero HLD files found.')
    file_list.sort(key=itemgetter(0))
    return file_list
    
def getInterFileInterval(file_list):
    NFILES = 20
    if len(file_list) <= NFILES:
        raise NoFilesError("Not enough HLD files to estimate inter-file interval.")
    dt = file_list[-1][0] - file_list[-1*(1+NFILES)][0]
    return float(dt / NFILES)

def getMostRecentFile(file_list):
    return os.path.basename(file_list[-1][1])

if __name__ == "__main__":
    mrf = getMostRecentFolder('/data/djpet/data/DAQ/', 'DJ_*')
    print(mrf)
    fl = listHLDfiles(mrf)
    print(getMostRecentFile(fl))
    print(getInterFileInterval(fl))
    try:
        listHLDfiles('.')
    except NoFilesError as e:
        print('Exception caught: ' + str(e) )
