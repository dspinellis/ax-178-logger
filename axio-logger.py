#!/usr/bin/env python
#
# Copyright 2022 Diomidis Spinellis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
AXIO MET AX-178 logger
"""

import argparse
from bitarray import bitarray
from bitarray.util import ba2int
from datetime import datetime
import serial
import sys
import time

def synchronize(port):
    """Synchronize reading to the data arrival rate"""
    # Values arrive every 380ms
    # A value takes 8 * (8 + 1 + 1) / 2400 = 33ms to transmit
    # Set a timeout to 100ms to avoid concatenating a partial value
    # with the next one
    port.timeout = 50
    port.read(16)
    while True:
        a = port.read(8)
        print(len(a))
        if len(a) == 8:
            # Set port timeout to handle the expected arrival rate
            port.timeout = 400
            return

class Mode:
    """Multimeter measurement mode"""
    def __init__(self, unit, divisor):
        self.unit = unit
        self.divisor = divisor


def bit_bytes(bits):
    """Return the bytes corresponding to the specified bit string"""
    return bitarray(bits, endian='little').tobytes()

modes = {
    bit_bytes('001010000'): Mode('V AC', 10000),
    bit_bytes('001010001'): Mode('%', 100),
    bit_bytes('001010010'): Mode('mV DC', 1000),
    bit_bytes('001010011'): Mode('nF', 100),
    bit_bytes('001010100'): Mode('V DC', 10000),
    bit_bytes('001010101'): Mode('Ohm', 100),
    bit_bytes('001010110'): Mode('mV AC DC', 100),
    bit_bytes('001010111'): Mode('uA AC', 100),
    bit_bytes('001011000'): Mode('dBm', 100),
    bit_bytes('001011001'): Mode('VF', 10000),
    bit_bytes('001011010'): Mode('mV AC', 1000),
    bit_bytes('001011011'): Mode('uA DC', 100),
    bit_bytes('001011100'): Mode('A DC', 10000),
    bit_bytes('001011110'): Mode('Hz', 1000),
    bit_bytes('001011111'): Mode('uA AC DC', 100),
}

def process(args, port):
    """Process data from the specified serial port"""
    synchronize(port)
    sep = ',' if args.csv else '\t'
    while True:
        a = port.read(8)
        if len(a) != 8:
            print('Synchronization lost; retrying', file=sys.stderr)
            synchronize(port)
            continue

        # Create a bit array from the non-value bytes read
        ba = bitarray(endian='little')
        ba.frombytes(a[0:3])

        # Numeric value; its scaling and sign depend on other bits
        numbers = ''.join([str(c) for c in a[3:8]])

        value = int(numbers)

        multiply_ten = ba[0]
        mode = ba[3:12]
        negative = int(ba[21])

        if args.raw:
            print(f"{ba} {mode} {negative} {numbers}")
            continue

        if mode.tobytes() not in modes:
            print(f"Unknown measurement mode {mode} (v={value})", file=sys.stderr)
            continue

        m = modes[mode.tobytes()]
        unit = m.unit

        value /= m.divisor


        if unit == 'Ohm':
            if int(ba[2]):
                unit = 'M Ohm'
                value /= 100
            elif int(ba[1]):
                unit = 'k Ohm'
                value /= 10

        if unit == '%':
            if int(ba[14]):
                unit = 'nF'
                value /= 1000

        if unit == 'nF':
            if int(ba[2]):
                unit = 'uF'
                value *= 10

        if unit == 'V AC':
            negative = 0
            if int(ba[1]):
                value *= 100

        if unit == 'mV DC' and int(ba[12]):
            unit = 'A AC'
            negative = 0
            value /= 10

        if unit == 'V DC' and int(ba[12]):
            unit = 'mA AC DC'
            value *= 10

        if unit == 'mV AC' and int(ba[12]):
            unit = 'A AC DC'
            value /= 10

        if unit == 'V AC' and int(ba[12]):
            unit = 'mA DC'
            #value /= 10

        if unit == 'dBm' and negative:
            unit = 'ma AC'
            value /= 10
            negative = 0

        if unit == 'uA AC':
            negative = 0

        if int(ba[0]):
            value *= 10

        if negative:
            value = -value

        if int(ba[13]):
            value = 'OVERFLOW'

        # Create timestamp
        if (args.unix_time):
            ts = time.time() + sep
        elif args.iso_time:
            ts = datetime.now().isoformat() + sep
        else:
            ts = ''

        print(f"{ts}{value}{sep}{unit}")

def main():
    """Program entry point"""
    parser = argparse.ArgumentParser(
        description='AXIO MET AX-178 logger')
    parser.add_argument('port',
                        help='Serial port from which to read data (e.g. /dev/ttyUSB0 or COM8)',
                        type=str)
    parser.add_argument('-c', '--csv',
                        help='Output comma-separated values',
                        action='store_true')

    parser.add_argument('-i', '--iso-time',
                        help='Prefix values with ISO timestamp',
                        action='store_true')

    parser.add_argument('-r', '--raw',
                        help='Print raw output',
                        action='store_true')

    parser.add_argument('-u', '--unix-time',
                        help='Prefix values with Unix Epoch timestamp',
                        action='store_true')

    args = parser.parse_args()

    port = serial.Serial(args.port,
                      baudrate=2400,
                      bytesize=serial.EIGHTBITS,
                      parity=serial.PARITY_NONE,
                      stopbits=serial.STOPBITS_ONE)
    try:
        process(args, port)
    except KeyboardInterrupt:
        port.close()
        sys.exit(0)

if __name__ == "__main__":
    main()
