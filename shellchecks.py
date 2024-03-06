import glob
import os
import os.path
from rootchecks import *
from operator import itemgetter

daq_path = '/data/DAQ/'

class NoFilesError(Exception):
    pass

def getMostRecentFolder(path, folder_name_pattern):

    """ Returns the path to a folder where the most recent HLD file was written.
    This function only checks files with a *.hld extension to avoid picking up
    file writes caused by the compression service which may write e.g. bz2 files
    to older directories."""
    hld_files = [(os.path.getmtime(entry), entry) for entry in glob.glob(path + '/' +folder_name_pattern + '/*.hld') if os.path.isfile(entry)]
    latest_hld_file = max(hld_files,key=itemgetter(0))[1] 
    return os.path.dirname(latest_hld_file)

def listHLDfiles(path):
    file_list = [(os.path.getmtime(entry), entry) for entry in glob.glob(path + '/*.hld') if os.path.isfile(entry)]
    if len(file_list) == 0:
        raise NoFilesError('Zero HLD files found.')
    file_list.sort(key=itemgetter(0))
    return file_list

def getInterFileInterval(file_list):
    NFILES = readFrequencyOfFiles()
    if len(file_list) <= NFILES:
        raise NoFilesError("Not enough HLD files to estimate inter-file interval.")
    dt = file_list[-1][0] - file_list[-1*(1+NFILES)][0]
    return float(dt / NFILES)

def getMostRecentFile(file_list):
    return os.path.basename(file_list[-1][1])

if __name__ == "__main__":
    mrf = getMostRecentFolder(str(daq_path), 'DJ_*')
    print(mrf)
    fl = listHLDfiles(mrf)
    print(getMostRecentFile(fl))
    print(getInterFileInterval(fl))
    try:
        listHLDfiles('.')
    except NoFilesError as e:
        print('Exception caught: ' + str(e))
