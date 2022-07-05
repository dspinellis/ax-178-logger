# AXIO MET AX-178 multimeter logger
This program allows logging of the AXIO MET AX-178 multimeter from
the command line.
It was developed by reverse-engineering the sent data.
The code has been tested on Debian Linux.

## Installation
Install the  `bitarray` and `serial` packages, e.g. through
the following commands.

```
virtualenv venv -p /usr/bin/python3
. venv/bin/activate
pip install bitarray pyserial
```

## Execution
* Setup the multimeter to the desired value
  (manual range, hold, and min/max measurements are not supported)
* Press and hold the hold button to start sending values
* Start the program with a command such as `./axio-logger.py /dev/ttyUSB0`
  Values appear on the command's standard output.
* Run `axio-logger.py -h` to see available command-line options
* If you see an error, such as
  `Unknown measurement mode bitarray('100000000') (v=9250161)`
  where `v` doesn't match what you see on the screen, you've hit a
  serial port synchronization error.
  Stop the program (e.g. with `^C`) and start it again.
