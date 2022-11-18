import unittest
import socket
import logging
from webmonitoring import readVacuumData, checkVacuumData, writeDataToDB
import meteo
from datetime import datetime
import datetime as dt

logging.basicConfig(filename='unittest.log', level=logging.DEBUG,
                                        format = '%(asctime)s - [%(name)s] %(levelname)s: %(message)s',
                                        datefmt = '%m/%d/%Y %I:%M:%S %p')

SERVER_ADDRESS = ("172.16.32.78", 5143)

class TestData(unittest.TestCase):
    def test_receive(self):
        
        data = readVacuumData(SERVER_ADDRESS)
        # TODO: assert no throw

    def test_check_vacuum_data(self):

        state = {
                "x" : 0,
                "meteo_data" : [],
                "meteo_time_offset" : 0, # in seconds
                "readout_time" : None,
                "monitoring_file" : "-",
                "last_hld_file" : "-",
                "event_counts" : -1,
                "events_sum" : 0,
                "reset_events": False
                }
        

        checkVacuumData(state)

        self.assertIn('meteo_data', state)
        self.assertIn('P1', state['meteo_data'])

        # print(state)

    def test_dict_to_tuple(self):

        data = {'MONITORING_FILE': '-', 'EVENT_COUNTS': -1, 'SERVER_TIME': '2022-11-17 11:51:54', 'MEASUREMENT_TIME': '2022-11-17 11:51:54', 'P2': {'unit': 'mbar', 'value': 0.0436}, 'READ_TIME': '2022-11-17T11:51:54', 'EVENTS_SUM': 0, 'P1': {'unit': 'mbar', 'value': 1.78}}

        tuple_data = meteo._dict2tuple(data)
        self.assertEqual(len(tuple_data), 13) 

    def test_db_write(self):

        data = {'MONITORING_FILE': '-', 'EVENT_COUNTS': -1, 'SERVER_TIME': '2022-11-17 11:51:54', 'MEASUREMENT_TIME': '2022-11-17 11:51:54', 'P2': {'unit': 'mbar', 'value': 0.0436}, 'READ_TIME': '2022-11-17T11:51:54', 'EVENTS_SUM': 0, 'P1': {'unit': 'mbar', 'value': 1.78}}

        state = {"meteo_data" : data}
        meteo.initDB('./test.db')
        writeDataToDB(state)


    def test_get_records(self):
        
        now = datetime.now()
        retro_shift = dt.timedelta(days=-1)

        records = meteo.getRecordsSince(now + retro_shift) 
        
        print(meteo.recreateTextFile(list(records)))



