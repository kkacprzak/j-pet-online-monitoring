import json
import logging
import re
import select
import signal
import socket
from datetime import datetime
from math import nan
from time import sleep

import serial

GAUGE_DEVICE = "/dev/ttyUSB0"
HYTELOG_DEVICE = "/dev/ttyUSB0"
PORT_NUMBER = 5143

sensor_status = {
    0: "Measurement data OK",
    1: "Underrange",
    2: "Overrange",
    3: "Sensor error",
    4: "Sensor off",
    5: "No sensor",
    6: "Identification error",
    7: "Unable to decode readout",
}


def parseGaugeData(data):
    # data looks like b'0,+7.8900E+02\rx15\r'

    try:
        data = data.decode("ascii", "ignore")
    except UnicodeDecodeError as err:
        logging.error(
            "Pressure readout decoding error: {} for data: {}".format(str(err), data)
        )
        return (0.0, 7)

    try:
        status = int(data.split(",")[0])
        data = re.findall("\d+\.\d+E[+5D-]\d+", data)
        data = data[0]
        readout = float(data)
    except Exception as err:
        logging.error(
            "Status or pressure decoding error: {} for data: {}".format(str(err), data)
        )
        return (0.0, 7)

    return (readout, status)


def readGauge(gauge_no):
    serial_port = serial.Serial(GAUGE_DEVICE, 9600, timeout=1)
    query = "PR{}\r\n".format(gauge_no)

    # try to send query until ACK is received
    attempt_counter = 0
    while True:
        serial_port.write(bytearray(query, "ascii"))
        sleep(0.2)
        response = serial_port.readline()
        attempt_counter = attempt_counter + 1
        if response == b"\x06\r\n":
            print("ACK received after {} attempts.".format(attempt_counter))
            break
        if attempt_counter > 9:
            raise Exception(
                "Response for the gauge {} is not ACK after 10th attempt. Received response: {}.".format(
                    gauge_no, response
                )
            )

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
        logging.warning(
            "Pressor sensor {} error status: {}".format(gauge_no, sensor_status[status])
        )
        reading = nan

    return reading


def formatData(pressure_data, hytelog_data):
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%S")

    data = {
        "MEASUREMENT_TIME": timestamp,
        "P1": {"value": pressure_data[0], "unit": "Pa"},
        "P2": {"value": pressure_data[1], "unit": "Pa"},
        "T": {"value": hytelog_data[0], "unit": "C"},
        "H": {"value": hytelog_data[1], "unit": "%"}
    }


def readTempAndHumidity():

    serial_port = serial.Serial(GAUGE_DEVICE, 38400, timeout=1, parity=serial.PARITY_ODD)

    sync_counter = 0
    chunk = b''
    while True:
        chunk = serial_port.readline()
        if chunk == b'\r\n':
            if sync_counter == 2:
                break
            else:
                sync_counter = 0
                continue
        elif chunk == b'\tX\tX\tX\tX':
            sync_counter += 1
            continue
        else:
            continue

    chunk = serial_port.readline()
    serial_port.close()
    temperature = float(chunk[0:4])/100.
    humidity = float(chunk[5:10])/200.

    print(temperature, humidity)


if __name__ == "__main__":

    while True:

        readTempAndHumidity()
        sleep(2)

# if __name__ == "__main__":
#     should_continue = True
#
#     # register SIGINT handler to exit gracefully on Ctrl-C
#     def signal_handler(sig, frame):
#         global should_continue
#         logging.info("Ctrl-C/SIGINT received, exiting.")
#         should_continue = False
#
#     signal.signal(signal.SIGINT, signal_handler)
#
#     logging.basicConfig(
#         filename="vacuum_readout.log",
#         level=logging.DEBUG,
#         format="%(asctime)s - %(levelname)s: %(message)s",
#         datefmt="%m/%d/%Y %I:%M:%S %p",
#     )
#
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     sock.settimeout(None)
#     sock.bind(("", PORT_NUMBER))
#
#     epoll = select.epoll()
#     epoll.register(sock.fileno(), select.EPOLLIN)
#
#     while should_continue:
#         events = epoll.poll(1)
#         for fileno, event in events:
#             if fileno == sock.fileno():
#                 query, client_address = sock.recvfrom(1024)
#
#                 try:
#                     pressure_data = (readGauge(1), readGauge(2))
#                 except Exception as err:
#                     logging.error("Error reading gauges: {}".format(str(err)))
#                     pressure_data = (0, 0)
#
#                 logging.info(
#                     "Presure data: "
#                     + str(pressure_data[0])
#                     + ", "
#                     + str(pressure_data[1])
#                 )
#
#                 data = bytearray(formatData(pressure_data), "utf-8")
#                 sock.sendto(data, client_address)
#                 logging.info("data has been sent")
#
#     sock.close()
