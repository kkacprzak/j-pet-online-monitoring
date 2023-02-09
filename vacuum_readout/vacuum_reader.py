import serial
from time import sleep
import logging
from math import nan
from datetime import datetime
import socket
import signal
import re

sensor_status = {
    0 : "Measurement data OK",
    1 : "Underrange",
    2 : "Overrange",
    3 : "Sensor error",
    4 : "Sensor off",
    5 : "No sensor",
    6 : "Identification error",
    7 : "Unable to decode readout"
}

def parseGaugeData(data):

    # data looks like b'0,+7.8900E+02\rx15\r'
    
    try:
        data = data.decode('ascii', 'ignore')
    except UnicodeDecodeError as err:
        logging.error("Pressure readout decoding error: {} for data: {}".format(str(err), data))
        return (0.0, 7)

#    data = data.split("\r")[0]

    
    try:
        status = int(data.split(",")[0])
#        data = data.split(",")[1]
        data = re.findall("\d+\.\d+E[+5D-]\d+", data)
        data = data[0]
        readout = float(data)
    except Exception as err:
        logging.error("Status or pressure decoding error: {} for data: {}".format(str(err), data))
        return (0.0, 7)
        
    return (readout, status)

def readGauge(gauge_no):
    
    serial_port = serial.Serial('/dev/ttyS1', 9600, timeout=1)
    query = "PR{}\r\n".format(gauge_no)

    # try to send query until ACK is received
    attempt_counter = 0
    while True:
        serial_port.write(bytearray(query, 'ascii'))
        sleep(0.2)
        response = serial_port.readline()
        attempt_counter = attempt_counter + 1
        if response == b'\x06\r\n':
            print("ACK received after {} attempts.".format(attempt_counter))
            break
        if attempt_counter > 9:
            raise Exception("Response for the gauge {} is not ACK after 10th attempt. Received response: {}.".format(gauge_no, response))

    # at this stage we should be ready to receive data
    sleep(0.2)

    # signal we're ready to read the data (send ENQ)
    serial_port.write(b"\05\r\n")
    sleep(0.2)
    response = serial_port.readline()
    serial_port.close()
    
    # parse the retuned data
    reading, status = parseGaugeData(response)

    if status != 0:
        logging.warning("Pressor sensor {} error status: {}".format(gauge_no, sensor_status[status]))
        reading = nan

    return reading

def readMeteoData():
    
    serial_port = serial.Serial('/dev/ttyUSB0', 19200, parity=serial.PARITY_NONE, timeout=10)
    query = b'Q'
    serial_port.write(query)
    sleep(0.2)
    
    is_data = True
    data = []
    
    while is_data:
        payload = serial_port.readline()
        if len(payload) == 0:
            is_data = False
        else:
            payload = payload.decode('utf-8').strip()
            data.append(payload)
    
    serial_port.close()
    
    return data

def formatMeteoData(meteo_data, vacuum_data):
    current_time = datetime.now()
    current_time.strftime("%Y-%m-%d %H:%M:%S")
    return_string = current_time.strftime("%Y-%m-%d %H:%M:%S") + " > "

    # use a dummy data string for now
    meteo_data[10].replace("H1", "H0")
    meteo_data[11].replace("H2", "H1")

    meteo_string = "; ".join(meteo_data)
    #meteo_string = "#0: 24.90; #1: 22.20; #2: 19.40; #3: 20.50; #4: 27.90; #5: 20.20; #6: 19.20; #7: 22.10; #8: 25.10; #9: 22.90; H0: 1.00; H1: 25.80; P: 99037.00 Pa;"

    return_string += meteo_string
    return_string += "P1: {} mbar; P2: {} mbar;".format(*vacuum_data)

    return return_string

if __name__ == "__main__":

    # register SIGINT handler to exit gracefully on Ctrl-C
    def signal_handler(sig, frame):
        logging.info("Ctrl-C/SIGINT received, exiting.")
        sock.close()        

    signal.signal(signal.SIGINT, signal_handler)

    logging.basicConfig(filename='sensors.log',level=logging.DEBUG,
                        format = '%(asctime)s - %(levelname)s: %(message)s',
                        datefmt = '%m/%d/%Y %I:%M:%S %p')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(None)
    sock.bind(('', 5143))

    while True:
        query, client_address = sock.recvfrom(1024)
        if query == b'Q':
            logging.info("received data query")

            meteo_data = readMeteoData()

            try:
                pressure_data = (readGauge(1), readGauge(2))
            except Exception as err:
                logging.error("Error reading gauges: {}".format(str(err)))
                pressure_data = (0, 0)

            print(pressure_data[0])
            print(pressure_data[1])        
            data = bytearray(formatMeteoData(meteo_data, pressure_data), 'utf-8') 
            sock.sendto(data, client_address)
            logging.info("data has been sent")
            
#    data = bytearray(formatMeteoData(readMeteoData(), (readGauge(1), readGauge(2))), 'utf-8') 
#    print(data)
    
    sock.close()
