# j-pet-online-monitoring
Software for continuous monitoring of the datataking conditions in the J-PET experiment

## Python requirements:
* Python2
* CherryPy<18.0.0
* numpy
* matplotlib
* backports.lzma

## Example preparation of a local virtual environment
```sh
pip2 install --user virtualenv
python2 -m virtualenv online_monitoring
source online_monitoring/bin/activate
pip2 install CherryPy
pip2 install matplotlib
pip2 install backports.lzma
```

## Before first usage:
Create the directory for images with plots in the working directory where the program will be executed:

`mkdir plots/`

## Running:
`python2 webmonitoring.py`

You should be able to access the monitoring page in a web browser at the address of the server and port 8000.    

