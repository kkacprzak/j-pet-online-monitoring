import sqlite3
from datetime import datetime
import dateutil.parser as dp
import math
import logging

table_name = 'conditions'

db_filename = ""

logger = logging.getLogger('meteo')

def initDB(filename):

    global db_filename
    
    db_filename = filename
    
    con = None
    
    try:
        con = sqlite3.connect(db_filename)
        cursor = con.cursor()

        cursor.execute(
            '''SELECT name FROM sqlite_master WHERE type='table' 
            and name='%s';''' % (table_name))

        if len(cursor.fetchall()) == 0: # table did not exist
            cursor.execute(
                '''CREATE TABLE %s 
                (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                STATION_TIME TEXT,
                SERVER_TIME TEXT,
                P_ATM REAL,
                P1 REAL,
                P2 REAL,
                HUM1 REAL,
                HUM2 REAL,
                T0 REAL,
                T1 REAL,
                T2 REAL,
                T3 REAL,
                T4 REAL,
                T5 REAL,
                T6 REAL,
                T7 REAL,
                T8 REAL,
                T9 REAL,
                LAST_HLD TEXT
                )''' % (table_name))
            logger.debug("DB table did not exist, creating one.")
    
    except sqlite3.Error, e:

        logger.error( "Error {}:".format(e.args[0]))
        return

    finally:
        if con:
            con.close()

def extractValue(line, position):
    words = line[position].split(' ')
    value = float(words[2]) 
    return value
    
def extractTimestamp(line):
    words = line[0].split(' ')
    return datetime.strptime(words[0]+" "+words[1], '%Y-%m-%d %H:%M:%S').isoformat()

def makeData(line, read_time, last_hld):

    data = []
    line = line.strip()
    line = line.replace('>', ';').split(';')
    data.append(extractTimestamp(line))
    data.append(read_time.isoformat())
    for pos in xrange(1,16):
        data.append(extractValue(line, pos))
    data.append(last_hld)
    return data

def writeRecord(line, timestamp, hld_file):
    data = makeData(line, timestamp, hld_file)
    __writeRecord(data)
    return data
    
def __writeRecord(data):
    
    con = None

    logger.debug( "ATTEMPTING TO OPEN DB: " + db_filename)
    
    try:
        con = sqlite3.connect(db_filename)
        cursor = con.cursor()

        sql = '''INSERT INTO %s(STATION_TIME,SERVER_TIME,
        T0,T1,T2,T3,T4,T5,T6,T7,T8,T9,
        HUM1,HUM2,P_ATM,P1,P2,
        LAST_HLD) 
        VALUES(
        ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?
        );''' % table_name
        
        cursor.execute(sql , tuple(data))
        con.commit()

        logger.debug("INSERT result: " + str(cursor.fetchall()))
        
    except sqlite3.Error, e:
        logger.error( "Error in inserting {}:".format(e.args[0]))
        return
    finally:
        if con:
            con.close()

def getRecordsSince(beg):
    end = datetime.now()
    return getRecordsBetween(beg, end)
    
def getRecordsBetween(beg, end):

    con = None
    logger.debug( "ATTEMPTING TO OPEN DB: " + db_filename + " FOR READING")
    
    try:
        con = sqlite3.connect(db_filename)
        cursor = con.cursor()

        sql = """SELECT *
        FROM "%s" WHERE datetime(SERVER_TIME) BETWEEN datetime(?) and datetime(?) 
        order by datetime(SERVER_TIME) asc;""" % (table_name,)

        cursor.execute(sql, (beg.isoformat(), end.isoformat()))        
        return cursor.fetchall()

    except sqlite3.Error, e:
        logger.error( "Error in querying DB {}:".format(e.args[0]))
        return ()
    finally:
        if con:
            con.close()

def recreateTextFile(data):
    '''This method creates a text buffer mimicking the format
    of the text log files produced by the meteo station'''

    buffer = ""

    for entry in data:
        line = dp.parse(entry[1]).strftime('%Y-%m-%d %H:%M:%S') + ' > '
        for i in xrange(10):
            line = line + '#' + str(i) + ': ' + str(entry[8+i]) + '; '
        line = line + 'H0: ' + str(entry[6]) + '; '
        line = line + 'H1: ' + str(entry[7]) + '; '
        line = line + 'P: ' + str(entry[3]) + ' Pa; '
        line = line + 'P1: ' + str(entry[4]) + ' Pa; '
        line = line + 'P2: ' + str(entry[5]) + ' Pa;'
        line = line + "\n"
        buffer = buffer + line
        
    return buffer

if __name__ == "__main__":

    data = (
        '2019-01-14T14:43:21',
        '2019-01-14T15:43:21',
        1024.,
        0.1,
        0.43,
        0.8,
        0.21,
        24.1, 23.3, 19.0, 39.0, 43.1, 12.1, -1.2, 21.9, 21.8, 27.2, 100.3,
        'dabc_2342367.hld'
    )

    # the ultimate test and example of usage
    
    initDB('test2.sqlite')    

    with open('meteo_data.txt') as f:
        for line in f:
            writeRecord(line, datetime.now(), 'zyx')

