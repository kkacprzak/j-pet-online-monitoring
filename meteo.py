from collections import OrderedDict
import sqlite3
from datetime import datetime
import dateutil.parser as dp
import logging
import lzma

TABLE_NAME = 'conditions'
db_filename = ""
last_db_backup_time = datetime(1970,1,1)

DATA_LABELS = OrderedDict([
    ('MEASUREMENT_TIME', 'TEXT'),
    ('SERVER_TIME', 'TEXT'),
    ('P_ATM', 'REAL'),
    ('P1', 'REAL'),
    ('P2', 'REAL'),
    ('HUM1', 'REAL'),
    ('HUM2', 'REAL'),
    ('T0', 'REAL'),
    ('T1', 'REAL'),
    ('LAST_HLD_FILE', 'TEXT'),
    ('LAST_MONITORING_FILE', 'INTEGER'),
    ('EVENT_COUNTS', 'INTEGER'),
    ('EVENTS_SUM', 'INTEGER')
    ])

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
            and name='%s';''' % (TABLE_NAME))

        query = ', '.join([label + ' ' + DATA_LABELS[label] for label in DATA_LABELS])
        query = 'CREATE TABLE ' + TABLE_NAME + ' (ID INTEGER PRIMARY KEY AUTOINCREMENT,' + query + ');'

        if len(cursor.fetchall()) == 0: # table did not exist
            cursor.execute(query)
            logger.debug("DB table did not exist, creating one.")
    
    except sqlite3.Error as e:
        logger.error( "Error {}:".format(e.args[0]))
        return

    finally:
        if con:
            con.close()

def _extractValue(data, label):
    """ Checks is the provided label exists as a key in the data dictionary
        and whether it is a scalar value (in which case it is directly returned)
        or a composite dictionary value (used e.g. for values with units)
        for which only the value is returned without unit.

        In case the label is not found in data, returns a default value.
    """
    label = label.upper()
    if label in data:
        if isinstance(data[label], dict) and 'value' in data[label]:
            return data[label]['value']
        else:
            return data[label]
    else:
        return 0.0

def _dict2tuple(data):
    values = []

    for label in DATA_LABELS:
        values.append(_extractValue(data, label))
    return tuple(values)
    
def writeRecord(data):
    data = _dict2tuple(data)
    _writeRecord(data)
    
def _writeRecord(data):
    
    con = None

    logger.debug("ATTEMPTING TO OPEN DB: " + db_filename)
    
    try:
        con = sqlite3.connect(db_filename)
        cursor = con.cursor()

        sql = 'INSERT INTO %s(' % TABLE_NAME
        sql += ', '.join(DATA_LABELS.keys())
        sql += ') VALUES('
        sql += ', '.join(['?' for _item in DATA_LABELS])
        sql += ');'

        cursor.execute(sql, data)
        con.commit()

        logger.debug("INSERT result: " + str(cursor.fetchall()))
        
    except sqlite3.Error as e:
        logger.error( "Error in inserting {}:".format(e.args[0]))
        return
    finally:
        if con:
            con.close()

def _tuple2dict(tuple_data):
    d = {}
    index = 0
    for item in DATA_LABELS:
        d[item] = tuple_data[index]
        index += 1
    return d

def getRecordsSince(beg):
    end = datetime.now()
    return getRecordsBetween(beg, end)
    
def getRecordsBetween(beg, end):

    con = None
    logger.debug( "ATTEMPTING TO OPEN DB: " + db_filename + " FOR READING")
    
    try:
        con = sqlite3.connect(db_filename)
        cursor = con.cursor()

        sql = 'SELECT '
        sql += ', '.join(DATA_LABELS.keys())
        sql += ' FROM %s' % TABLE_NAME
        sql += ' WHERE datetime(SERVER_TIME) BETWEEN datetime(?) and datetime(?)'
        sql += ' order by datetime(SERVER_TIME) asc;'

        cursor.execute(sql, (beg.isoformat(), end.isoformat()))        
        return map(_tuple2dict, cursor.fetchall())

    except sqlite3.Error as e:
        logger.error( "Error in querying DB {}:".format(e.args[0]))
        return ()
    finally:
        if con:
            con.close()

def recreateTextFile(data):
    '''This method creates a text buffer with conditions data in TSV format'''
    buffer = ""

    def makeFloat(x):
        if x is None:
            return "NaN"
        else:
            return str(x)
        
    headers = DATA_LABELS
    header_line = "\t".join(headers) + "\n"

    buffer += header_line

    for entry in data:

        values = [str(entry[item]) for item in DATA_LABELS]
        line = "\t".join(values) + "\n"

        # line = dp.parse(entry[1]).strftime('%Y-%m-%d %H:%M:%S') + ' > '
        # for i in xrange(10):
        #     line = line + '#' + str(i) + ': ' + makeFloat(entry[8+i]) + '; '
        # line = line + 'H0: ' + makeFloat(entry[6]) + '; '
        # line = line + 'H1: ' + makeFloat(entry[7]) + '; '
        # line = line + 'P: ' + makeFloat(entry[3]) + ' Pa; '
        # line = line + 'P1: ' + makeFloat(entry[4]) + ' Pa; '
        # line = line + 'P2: ' + makeFloat(entry[5]) + ' Pa;'
        # line = line + "\n"

        buffer += line
        
    return buffer

def dumpDBtoFile(db_backup_file = './db_backup.sql'):
    '''Creates an SQL file from the contents of the SQLite DB.
    This is intended for periodic backup of the DB.'''
    
    global last_db_backup_time

    try:
        con = sqlite3.connect(db_filename)
        
        with lzma.open(db_backup_file+'.xz', 'w') as f:
            for line in con.iterdump():
                f.write(str.encode('%s\n' % line))

        logger.debug("DB contents were dumped to an SQL file:  " + str(db_backup_file))
        last_db_backup_time = datetime.now()

    except sqlite3.Error:
        logger.error("Error in dumping the DB to an SQL file.")
        return
    finally:
        if con:
            con.close()

    return


if __name__ == "__main__":
    pass
    # data = (
    #     '2019-01-14T14:43:21',
    #     '2019-01-14T15:43:21',
    #     1024.,
    #     0.1,
    #     0.43,
    #     0.8,
    #     0.21,
    #     24.1, 23.3, 19.0, 39.0, 43.1, 12.1, -1.2, 21.9, 21.8, 27.2, 100.3,
    #     'dabc_2342367.hld'
    # )

    # # the ultimate test and example of usage
    
    # initDB('test2.sqlite')    

    # with open('meteo_data.txt') as f:
    #     for line in f:
    #         writeRecord(line, datetime.now(), 'zyx')

