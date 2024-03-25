from ROOT import TFile
import glob
import os
import os.path
from operator import itemgetter

file = 'reference/reference.root'

RAW_DATA_PATH = '/data/DAQ/'
base_path = '/home/jpet/monitoring/j-pet-online-monitoring/data_monitoring/'
events_histo_name = 'EventCategorizer subtask 5 stats/lifetime_2g_prompt'

def getEntriesFromHisto(filename):
    f = TFile(str(base_path)+ 'web/rootfiles/' + str(filename), 'OPEN')
    h = f.Get(events_histo_name)
    n = h.GetEntries()
    f.Close()
    return n
    
def getMostRecentMonitoringFile():
    list = [(os.path.getmtime(entry), os.path.split(entry)[1]) for entry in glob.glob(str(base_path)+'web/rootfiles/*.root') if os.path.isfile(entry) and "summary" not in os.path.split(entry)[1]]
    return max(list,key=itemgetter(0))[1]

def readFrequencyOfFiles():
    freq = -1
    with open(str(base_path)+'frequency.txt', 'r') as f:
        freq = int(f.read())
    return freq
        
def calculateEventsIncrement(old_count, new_count, files_between):

    avg_count = 0.5 * (old_count + new_count)
    return avg_count * readFrequencyOfFiles()
    
if __name__ == '__main__':
    print(getEntriesFromHisto(getMostRecentMonitoringFile()))
    print(readFrequencyOfFiles())
