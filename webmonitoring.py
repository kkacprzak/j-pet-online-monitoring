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
import signal
import socket
import sys
import os
import json

import meteo
import plot

plots_path = 'plots/'
view_monitoring_files_page = 'http://0.0.0.0:8080/'

db_path = './conditions_db.sqlite'
db_backup_path = './db_backup/'

web_assets_dir = '/home/jpet/monitoring/j-pet-online-monitoring/assets/'

update_time = 300 # seconds

# address of the computer reading the meteo and vacuum
meteo_station_address = ("192.168.0.65", 5143)

# for writing to DB
meteo.initDB(db_path)

# init logging
log_file_name = 'jlab_conditions_monitoring_' + time.strftime('%d-%m-%Y_%H-%M') + '.log'
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
    "last_hld_file" : "-",
    "monitoring_file" : "-",
    "event_counts" : -1,
    "events_sum" : 0,
    "reset_events": False,
    "inter_file_interval" : readFrequencyOfFiles()
}

def readVacuumAndHytelogData(server_data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10.0)

    sock.sendto(b"Q", server_data)
    try:
        data = sock.recv(1024) 
    except socket.timeout:
        logger.error("Timeout reached waiting for vacuum data, skipping readout")
        raise Exception
    finally:
        sock.close()
    logger.debug("Received data from vacuum server: " + str(data))
    return data
        
def checkVacuumAndHytelogData(S):

    S['meteo_data'] = None

    try:
        data = readVacuumAndHytelogData(meteo_station_address)
    except Exception:
        logger.error("readVacuumAndHytelogData failed, skipping this readout")
        return
    
    read_time = datetime.now()
    data = json.loads(data.decode())
    data['SERVER_TIME'] = read_time.strftime('%Y-%m-%dT%H:%M:%S')
    for label in ('LAST_HLD_FILE', 'MONITORING_FILE','EVENT_COUNTS', 'EVENTS_SUM'):
        data[label] = S[label.lower()]
    
    S["meteo_data"] = data

    # check time offset between meteo028 PC and server
    dt = dp.parse(data['MEASUREMENT_TIME']) - read_time
    S["meteo_time_offset"] = dt.total_seconds()

def writeDataToDB(S):
    
    if S['meteo_data'] is None:
        logger.debug('Conditions data empty, last readout likely failed. Skipping writing to DB.')
        return

    meteo.writeRecord(S["meteo_data"])
    logger.debug("Written data to DB: " + json.dumps(S["meteo_data"]))

def getDataForPlots(S):
    now = datetime.now()
    retro_shift = dt.timedelta(days=-1)
    S["meteo_data"] =  meteo.getRecordsSince(now + retro_shift)

def restoreLastReadout(S):
    last_readout = list(meteo.getLastReadout())
    if len(last_readout) == 0:
        S["events_sum"] = 0
    else:
        S["events_sum"] = int(last_readout[-1]["EVENTS_SUM"])
    
def makePlots(S):
    data = list(S["meteo_data"])
    plot.plotMeteoStuff(data, plots_path)
    plot.plotEventCounts(data, plots_path)
    
def backupDB(S):
    timestamp = state["readout_time"].strftime('%Y-%m-%d %H:%M:%S')
    if (state["readout_time"] - meteo.last_db_backup_time).days > 0:
        meteo.dumpDBtoFile(db_backup_path + 'db_' + timestamp + '.sql')

def checkDataMonitoring(S):
    monitoring_file = getMostRecentMonitoringFile()
    folder = getMostRecentFolder(str(daq_path), 'DJ_*')
    try:
        file_list = listHLDfiles(folder)
        S["last_hld_file"] = getMostRecentFile(file_list)
    except NoFilesError as e:
        logger.error("Error in finding most recent HLD file: " +  str(e) + ". Most recent file is not updated.")

    try:
        S["inter_file_interval"] = getInterFileInterval(file_list)
    except NoFilesError as e:
        logger.error("Error in estimating inter-file interval: " +  str(e) + ". Interval is not updated.")

    if monitoring_file != S["monitoring_file"]:
        prev_mon_file = monitoring_file
        curr_mon_file = S["monitoring_file"]
        S["monitoring_file"] = monitoring_file
        event_counts = getEntriesFromHisto(S["monitoring_file"])
        if S["reset_events"]:
            S["events_sum"] = 0
            logger.info("Resetting intergrated events counter by user request.")
            S["reset_events"] = False

        S["event_counts"] = event_counts
            
        if prev_mon_file != '-':
            events_between = (datetime.strptime(monitoring_file[0:16], "%Y_%m_%d_%H_%M") - datetime.strptime(S["monitoring_file"][0:16], "%Y_%m_%d_%H_%M")).total_seconds() / S["inter_file_interval"]
            S["events_sum"] = S["events_sum"] + calculateEventsIncrement(S["event_counts"], event_counts, events_between)

        
checks = (
    checkDataMonitoring,
    checkVacuumAndHytelogData,
    writeDataToDB,
    backupDB,
    getDataForPlots,
    makePlots
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
        file = getMeteoLogFile()
        plotMeteoStuff(file, plots_path)
        file.close()

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
            <TITLE>J-PET DAQ Monitoring</TITLE>
            <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
            <meta http-equiv="Pragma" content="no-cache" />
            <meta http-equiv="Expires" content="0" />
            <meta http-equiv="refresh" content="%d">
            <link rel="stylesheet" href="./assets/style.css">
            <link rel="icon" href="favicon.ico" />
        </HEAD>
        <BODY>
            <div class="header">
                <img src="./assets/jpet-logo.png" alt="J-PET Logo">
                <h1>DAQ Monitoring</h1>
            </div>
        
            <div class="section">
                <DIV><h2>Status at: %s (last readout time)</h2></DIV>
                <DIV><h3>Most recent HLD file: %s</h3></DIV>
                <DIV><h3>Most recent monitoring file: <a href="%s/monitoring.htm?filename=%s">%s</a></h3></DIV>
                <DIV><h3>Entries from most recent monitoring file: %s</h3></DIV>
                <DIV><h3>Average interval between subsequent HLD files: %s s</h3></DIV>
                <h3>Time difference between server and meteo PC: %d seconds</h3>
            </div>

            <div class="plots">
                <img SRC="./plots/temp.png"> 
                <img SRC="./plots/pressure.png">
                <img SRC="./plots/patm.png">
                <img SRC="./plots/humidities.png">
                <img SRC="./plots/events.png">
                <img SRC="./plots/integrated_events.png">
            </div>
        
            <div class="section">
                <h3>Reset counting:</h3>            
                <form class="button" method="get" action="reset_events">        
                <input type="submit" value="Reset!">
                </form>
            </div>
            <div class="section">
                <h3>Download conditions data for time range:</h3>

                <form class="button" method="get" action="fetch_records">
                From: <input type="date" id="records_range_beg" name="records_range_beg" value="2022-11-18">
                <input type="time" id="records_range_beg_time" name="records_range_beg_time" value="00:00">
                To: <input type="date" id="records_range_end" name="records_range_end" value="2022-11-18">
                <input type="time" id="records_range_end_time" name="records_range_end_time" value="23:59">
                <br>
                <input type="submit" value="Download data">
                </form>
            </div>
        
        </BODY>
        </HTML>
        """ % (update_time,
               readout_time,
               state["last_hld_file"],
               view_monitoring_files_page,
               state["monitoring_file"],
               state["monitoring_file"],
               str(state["event_counts"]),
               str(state["inter_file_interval"]),
               state["meteo_time_offset"]
        )

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
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="conditions_data.txt"'

        records = meteo.getRecordsBetween(beg_time, end_time)

        file_path = plots_path + '/conditions_data.txt'
        with open(file_path, 'w') as f:
            f.write(meteo.recreateTextFile(records))
        # buffer = StringIO.StringIO(meteo.recreateTextFile(records))
        # return serve_fileobj(buffer, "application/x-download", "attachment", name="conditions_data.txt")
        file_path = os.path.join(os.getcwd(), 'plots/conditions_data.txt')
        return cherrypy.lib.static.serve_file(file_path, 'application/x-download', 'attachment', os.path.basename(file_path))

if __name__ == '__main__':
    conf = {
        'global': {
            # Remove this to auto-reload code on change and output logs
            # directly to the console (dev mode).
            # 'environment': 'production',
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
        },
        '/assets': {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": web_assets_dir
        }
    }

    # Take care of signal handling

    def signal_handler(sig, frame):
        print('You pressed Ctrl+C!')
        logger.info("SIGINT received, cleaning up and exiting.")
        
        cherrypy.engine.exit()
        
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the server with the above app and the above config.
    def thread1(threadname):
        cherrypy.tree.mount(Root(), '/', conf)        
        cherrypy.config.update({'server.socket_host': '0.0.0.0', })
        cherrypy.config.update({'server.socket_port': 8001, })
        cherrypy.config.update({'log.screen': True,
                                'log.access_file': '',
                                'log.error_file': 'chpy_error.log'})
        cherrypy.engine.start()
        cherrypy.engine.block()

    # thread of the HTTP server
    thread1 = Thread( target=thread1, args=("HTTP Server thread", ) )
    thread1.daemon = True

    thread1.start()

    # control event loop

    restoreLastReadout(state)

    while True:
        time.sleep(update_time)
        for f in checks:
            state["readout_time"] = datetime.now()
            f(state)
