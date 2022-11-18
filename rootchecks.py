from ROOT import TFile
import glob
import os
import os.path
from operator import itemgetter

file = '2020_06_17_23_39_dabc_20169232158.root'

def getEntriesFromHisto(filename):
    f = TFile('/home/jpet/DataMonitoring2/web/rootfiles/' + str(filename), 'OPEN')
    h = f.Get('ThreeHitAnalysis subtask 6 stats/AnnhPointXYComp_after2DAngle_3 hit evts')
    n = h.GetEntries()
    f.Close()
    return n

def getMostRecentMonitoringFile():
    list = [(os.path.getmtime(entry), os.path.split(entry)[1]) for entry in glob.glob('/home/jpet/DataMonitoring2/web/rootfiles/*.root') if os.path.isfile(entry) and "summary" not in os.path.split(entry)[1]]
    return max(list,key=itemgetter(0))[1]

def readFrequencyOfFiles():
    freq = -1
    with open('/home/jpet/DataMonitoring2/frequency.txt', 'r') as f:
        freq = int(f.read())
    return freq
        
def calculateEventsIncrement(old_count, new_count):

    avg_count = 0.5 * (old_count + new_count)
    return avg_count * readFrequencyOfFiles()
    
if __name__ == '__main__':
    print(getEntriesFromHisto(getMostRecentMonitoringFile()))
