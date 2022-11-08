import logging
from threading import Thread
import datetime as dt
from datetime import datetime
import dateutil.parser as dp
from plot import plotMeteoStuff
from shellchecks import *
from rootchecks import *
import time
import cherrypy
from cherrypy.lib.static import serve_fileobj
import signal
import socket
import sys
import os
import StringIO

import meteo
import plot

plots_path = 'plots/'
daq_path = '/data/DAQ/'

db_path = './conditions_db.sqlite'
db_backup_path = '../db_backup/'

#update_time = 300 # seconds
update_time = 60 # seconds

# for connection to the meteo station
sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.settimeout(10.0)

server_address = ("172.16.32.107", 5143)

# for writing to DB
meteo.initDB(db_path)

# init logging
log_file_name = 'conditions_monitoring_' + time.strftime('%d-%m-%Y_%H-%M') + '.log'
logging.basicConfig(filename=log_file_name, level=logging.DEBUG,
                    format = '%(asctime)s - [%(name)s] %(levelname)s: %(message)s',
                    datefmt = '%m/%d/%Y %I:%M:%S %p')

# Create a custom logger
logger = logging.getLogger('web_monitoring')

# Silence info from Cherrypy
cherrypy.log.access_log.propagate = False
cherrypy.log.error_log.propagate = False

state = {
    "x" : 0,
    "meteo_data" : [],
    "meteo_time_offset" : 0, # in seconds
    "readout_time" : None,
    "monitoring_file" : "-",
    "event_counts" : -1,
    "events_sum" : 0,
    "reset_events": False
}


def readMeteoStation():
    sock.sendto("Q", server_address)
    try:
        data = sock.recv(1024) # buffer size is 1024 bytes
    except socket.timeout:
        logger.error("Timeout reached waiting for meteo data, skipping readout")
        raise Exception
    logger.debug("Received data from meteo server: " + data.strip())
    return data
        
def checkMeteoStation(S):
    try:
        line = readMeteoStation()
    except Exception as err:
        logger.error("readMeteoStation failed, skipping this readout")
        return
    
    read_time = datetime.now()
    data = meteo.writeRecord(line, read_time, 'zyx', S["monitoring_file"], S["event_counts"], S["events_sum"])

    logger.debug("Written data to DB: " + str(data))
    # check time offset between meteo028 PC and server
    dt = dp.parse(data[0]) - read_time
    S["meteo_time_offset"] = dt.total_seconds()
    
def getDataForPlots(S):
    now = datetime.now()
    retro_shift = dt.timedelta(days=-1)
    S["meteo_data"] =  meteo.getRecordsSince(now + retro_shift)

def makePlots(S):
    plot.plotMeteoStuff(S["meteo_data"], plots_path)
    plot.plotEventCounts(S["meteo_data"], plots_path)
    
def backupDB(S):
    timestamp = state["readout_time"].strftime('%Y-%m-%dT%H:%M:%S')
    if (state["readout_time"] - meteo.last_db_backup_time).days > 0:
        meteo.dumpDBtoFile(db_backup_path + 'db_' + timestamp + '.sql')

def checkDataMonitoring(S):
    monitoring_file = getMostRecentMonitoringFile()
    if monitoring_file != S["monitoring_file"]:
        S["monitoring_file"] = monitoring_file
        event_counts = getEntriesFromHisto(S["monitoring_file"])
        if S["reset_events"]:
            S["events_sum"] = 0
            logger.info("Resetting intergrated events counter by user request.")
            S["reset_events"] = False
        S["events_sum"] = S["events_sum"] + calculateEventsIncrement(S["event_counts"], event_counts)
        S["event_counts"] = event_counts
        
checks = (
    getDataForPlots,
    makePlots,
    checkDataMonitoring,
    checkMeteoStation,
    backupDB
)


class Root(object):
    
    def __init__(self):
        self.last_readout = 0
        self.recent_folder = ""
        self.recent_file = ""

    def loadStatus(self, current_time):
        if( abs(current_time - self.last_readout) < 120 ):
            #if last readout was closer than 120 s, do not read out again
            return self.last_readout
        # if last readout was older, read out all relavant parameters
        #
        file = getMeteoLogFile()
        plotMeteoStuff(file, plots_path)
        file.close()
        #
        self.recent_folder = getMostRecentFolder(daq_path, '????.??.??_????')
        self.recent_file = getMostRecentFile(self.recent_folder[1])
        self.last_readout = current_time
        return current_time

    @cherrypy.expose
    def index(self):

        global state

        if state["readout_time"] is not None:
            readout_time = state["readout_time"].strftime('%Y-%m-%d %H:%M:%S')
        else:
            readout_time = 'No readouts.'
            
        s = """
        <HTML>
        <HEAD>
        <TITLE>J-PET Monitoring</TITLE>
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
        <meta http-equiv="Pragma" content="no-cache" />
        <meta http-equiv="Expires" content="0" />
        <meta http-equiv="refresh" content="%d">
        </HEAD>
        <BODY BGCOLOR="FFFFFF">
        <DIV><h2>Status at: %s (last readout time)</h2></DIV>
        <DIV><h3>Most recent monitoring file: <a href="http://172.16.32.156/monitoring2/monitoring.htm?filename=%s">%s</a></h3></DIV>
        <DIV><h3>Entries from most recent monitoring file %s</h3></DIV>
        <CENTER>
        <IMG SRC="./plots/temp.png" ALIGN="BOTTOM"> 
        <IMG SRC="./plots/pressure.png" ALIGN="BOTTOM"> 
        <IMG SRC="./plots/patm.png" ALIGN="BOTTOM"> 
        <IMG SRC="./plots/humidities.png" ALIGN="BOTTOM"> 
        <IMG SRC="./plots/events.png" ALIGN="BOTTOM"> 
        <DIV>
        <IMG SRC="./plots/integrated_events.png" ALIGN="BOTTOM"> 
        <form method="get" action="reset_events">        
        <input type="submit" value="Reset counting">
        </form>
        </DIV>
        </CENTER> 
        <DIV><h3>Time difference between server and meteo PC: %d seconds</h3></DIV>
        <DIV>
        <form method="get" action="fetch_records">
        <h2>Download conditions data for time range:</h2>
        From: <input type="date" id="records_range_beg" name="records_range_beg" value="2019-01-16">
        <input type="time" id="records_range_beg_time" name="records_range_beg_time" value="00:00">
        To: <input type="date" id="records_range_end" name="records_range_end" value="2019-01-17">
        <input type="time" id="records_range_end_time" name="records_range_end_time" value="00:00">
        <br>
        <input type="submit" value="Download data">
        </form>
        </DIV>
        </BODY>
        </HTML>
        """ % (update_time,
               readout_time,
               state["monitoring_file"],
               state["monitoring_file"],
               str(state["event_counts"]),
               state["meteo_time_offset"]
        )
           #     self.recent_folder[1],
           #     os.path.basename(self.recent_file[1]),
           #     str(int(current_time-self.recent_file[0]))
           # )

        # <DIV><h3>Most recent folder %s</h3></DIV>
        # <DIV><h3>Most recent HLD file %s</h3></DIV>
        # <DIV><h3>Last access %s seconds ago</h3></DIV>
        
        return s

    @cherrypy.expose
    def reset_events(self):
        state["reset_events"] = True
        return "The event counter has been reset."
        
    @cherrypy.expose
    def fetch_records(self, records_range_beg, records_range_beg_time, records_range_end, records_range_end_time):

        beg_time = datetime.strptime(records_range_beg + 'T' + records_range_beg_time, '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(records_range_end + 'T' + records_range_end_time, '%Y-%m-%dT%H:%M')

        logger.debug("User requested DB data for time range " +
                     beg_time.isoformat() + " and " +
                     end_time.isoformat()
        )

        cherrypy.response.headers['Content-Type'] = "text/plain"
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="conditions.txt"'

        records = meteo.getRecordsBetween(beg_time, end_time)
        file_path = plots_path + '/conditions_data.txt'
        with open(file_path, 'w') as f:
            f.write(meteo.recreateTextFile(records))
        buffer = StringIO.StringIO(meteo.recreateTextFile(records))
        return serve_fileobj(buffer, "application/x-download", "attachment", name="conditions_data.txt")

if __name__ == '__main__':
    conf = {
        'global': {
            # Remove this to auto-reload code on change and output logs
            # directly to the console (dev mode).
#            'environment': 'production',
        },
        '/': {
            'tools.sessions.on': True,
            'tools.sessions.timeout': 60 * 10, # hours
        },
        '/plots': {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": "plots",
            "tools.staticdir.index": 'index.html',
            "tools.staticdir.root": os.getcwd(),
        }
    }

    # Take care of signal handling

    def signal_handler(sig, frame):
        print('You pressed Ctrl+C!')
        logger.info("SIGINT received, cleaning up and exiting.")

        
        sock.close()
        cherrypy.engine.exit()
        
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the server with the above app and the above config.
    def thread1(threadname):
        cherrypy.tree.mount(Root(), '/', conf)        
        cherrypy.config.update({'server.socket_host': '0.0.0.0', })
        cherrypy.config.update({'server.socket_port': 8000, })
        cherrypy.config.update({'log.screen': False,
                                'log.access_file': '',
                                'log.error_file': ''})
        cherrypy.engine.start()
        cherrypy.engine.block()

    # thread of the HTTP server
    thread1 = Thread( target=thread1, args=("HTTP Server thread", ) )
    thread1.daemon = True

    thread1.start()

    # control event loop
    while True:
        time.sleep(update_time)
        for f in checks:
            state["readout_time"] = datetime.now()
            f(state)
