import json
import datetime
import subprocess
import os
import logging
import sys

workdir = '/home/jpet/ModularMonitoring/DataMonitoring/'
rootfiles_dir = "web/rootfiles/"

os.chdir(workdir)

# setup a logger
logging.basicConfig(filename=str(workdir) + str(rootfiles_dir) + 'daily_summary.log',level=logging.DEBUG,
                    format = '%(asctime)s - %(levelname)s: %(message)s',
                    datefmt = '%m/%d/%Y %I:%M:%S %p')

logging.info('Attempting to create daily summary')

# add the created rootfile to the list
with open('web/files.json', mode='r') as file_list_json:
    file_list = json.load(file_list_json)

dt = datetime.datetime.today()
year = dt.year
month = dt.month
day_of_month = dt.day - 1 # we want a summary from yesterday

files_to_include = []

k = 0
while True:
    k = k + 1
    filename = file_list["files"][-1*k]
    if  'summary' in filename:
        continue
    if int(filename[8:10]) == day_of_month and int(filename[5:7]) == month:
        files_to_include.append(rootfiles_dir + filename)

    if int(filename[8:10]) == day_of_month-1 and int(filename[5:7]) == month:
        break

print(files_to_include)

summary_file_name = "{}_{}_{}_daily_summary.root".format(year, month, day_of_month)
command_line = ["/usr/local/bin/hadd", "-T", "-fk", rootfiles_dir + summary_file_name]
command_line.extend(files_to_include)

try:
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(
        command_line,
        stderr=subprocess.STDOUT,
        stdout=FNULL,
        close_fds=True
    )
    
except subprocess.CalledProcessError as e:
    logging.critical('Daily hadd crashed.')
    logging.debug('Command: ' + ' '.join(e.cmd))
    sys.exit(5)
    
logging.info('Daily summary created: ' + str(summary_file_name))
    
# add the created rootfile to the list
with open('web/files.json', mode='r') as file_list_json:
    file_list = json.load(file_list_json)

file_list["files"].append(summary_file_name)

with open('web/files.json', mode='w') as file_list_json:
    json.dump(file_list, file_list_json)
