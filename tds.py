#!/usr/bin/python3
"""Read channels or get a hardcopy of Tektronix TDS oscilloscopes via
serial port.

License:
    Copyright (C) 2013 Sönke Carstens-Behrens
    (carstens-behrens AT rheinahrcampus.de)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Usage:
    tds.py (-h | --help)
    tds.py [-hvd] [--hardcopy] [--channel=CHN] [--port=PORT]
           [--baud=BAUD] [--timeout=TIMEOUT] FILENAME

Arguments:
    FILENAME  Body of the output file name: a hardcopy will be name
              <filename>.png, channel data will be named <filename>.yaml
              or <filename>.dat, respectively.
Options:
    -h                  Print this help message.
    -v                  Print status messages.
    -d                  Store measurement values as columns in <filename>.dat
                        instead of the yaml format, first column contains
                        according time stems.
    --hardcopy          Store a hardcopy in png format as <filename>.png.
    --channel=CHN       Store measurement values of channel CHN in
                        <filename>.yaml in yaml format. It is possible to
                        assign more than one channel, e.g. chn=124 stores the
                        values of channels 1, 2 and 4 [default: None]
    --port=PORT         Serial communication port [default: /dev/ttyS0].
    --baud=BAUD       Symbol rate. Maximum of 19200 Bd unfortunately does not
                        seem to work [default: 9600].
    --timeout=TIMEOUT Timeout value in seconds for waiting on oscilloscope
                        response [default: 3]
"""

import os
import serial
import sys
import time
from docopt import docopt
import yaml  # pylint: disable=F0401


class Tds():
    """Provide interface to TDS oscilloscopes."""
    def __init__(self, opts):
        self.port = opts['--port']
        self.baudrate = opts['--baud']
        self.timeout = float(opts['--timeout'])
        self.verbose = opts['-v']
        self.connection = serial.Serial(
            port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        self.set('RS232:TRANSMIT LF')
        self.set('RS232:HARDFLAGGING ON')
        self.set('header off')        # NOTE: didn't work with capital letters?
        self.vprint('*IDN: {}'.format(self.get_id()))
        self.image = None

    def vprint(self, msg):
        """Print messages to command line in verbose mode."""
        if self.verbose:
            print(msg)

    def flush(self):
        """Flush data."""
        self.connection.flushInput()
        # self.connection.flushOutput()  # might be a source of error?

    def record(self, channel, convert=False):
        """Read a single channel."""
        self.vprint('trying to read channel {}'.format(channel))
        self.set('LOCK ALL')
        self.flush()
        self.set('DATA INIT\n')
        self.set('DATA:SOURCE CH{}\n'.format(channel))
        self.set('DATA:ENC ASCII\n')
        self.set('DATA:WIDTH 1\n')
        self.vprint('DATA: {}'.format((self.query('DATA?'))))
        xincr = self.query('WFMPRE:CH{}:XINCR?'.format(channel)).rstrip()
        ymult = self.query('WFMPRE:CH{}:YMULT?'.format(channel)).rstrip()
        yoff = self.query('WFMPRE:CH{}:YOFF?'.format(channel)).rstrip()
        yzero = self.query('WFMPRE:CH{}:YZERO?'.format(channel)).rstrip()
        self.vprint('xincr:{}, ymult:{}, yoff:{}, yzero:{}'.format(
            xincr, ymult, yoff, yzero))
        timevector = []
        if (xincr == ''):
            sys.exit('Error: could not read channel {}.'.format(channel))
        x_incr = float(xincr)
        y_off = float(yoff)
        y_mult = float(ymult)
        y_zero = float(yzero)
        for idata in range(2500):
            timevector.append(x_incr * idata)
        xsplit = self.query('CURVE?').split(',')
        data = []
        for idata in xsplit:
            if convert:
                data.append((float(idata) - y_off) * y_mult - y_zero)
            else:
                data.append(int(idata))
        self.vprint('Anzahl Datenpunkt: {}'.format(len(data)))
        self.set('UNLOCK ALL\n')
        return {'chn': channel, 'xincr': xincr, 'ymult': ymult, 'yoff': yoff,
                'yzero': yzero, 'data': data, 't': timevector}

    def hardcopy(self, filename):
        """Read a hardcopy of the screen."""
        self.set('LOCK ALL')
        self.flush()
        self.set('HARDCOPY:PORT RS232')
        self.set('HARDCOPY:FORMAT BMP')
        self.set('HARDCOPY:LAYOUT PORTRAIT')
        self.set('HARDCOPY START')
        time.sleep(1)
        self.image = self.get_waiting()
        time.sleep(1)
        while self.connection.inWaiting() > 0:
            self.image += self.get_waiting()
            self.vprint('{:2.1f} kB of some 40 kB'.format(
                len(self.image) / 1000))
            time.sleep(1)
        self.set('UNLOCK ALL\n')
        if len(self.image) < 30000:
            return False
        with open(filename, 'wb') as hardcopyfile:
            hardcopyfile.write(self.image)
        pngfile = '{}.png'.format(filename)
        command = 'convert {} {}'.format(filename, pngfile)
        os.system(command)
        command = 'rm -f {}'.format(filename)
        os.system(command)
        return True

    def set(self, command):
        """Send command to oscilloscope."""
        self.connection.flush()
        self.connection.write(bytearray('{}\n'.format(command), 'utf-8'))

    def get_waiting(self):
        """Read waiting hardcopy data from oscilloscope."""
        return self.connection.read(self.connection.inWaiting())

    def query(self, command):
        """Ask for data or information."""
        self.connection.flush()
        self.connection.write(bytearray('{}\n'.format(command), 'utf-8'))
        return self.connection.readline().decode('utf-8')

    def get_id(self):
        """Return ID of the oscilloscope."""
        return self.query('*IDN?')


def main(options):
    """Main program..."""
    tds = Tds(options)
    if len(tds.get_id()) < 5:
        print('Could not read device ID, aborting... Check your port.')
        return 6
    if options['--hardcopy']:
        if not tds.hardcopy(filename=options['FILENAME']):
            return 5
    measurements = []
    if options['--channel']:
        for channel in options['--channel']:
            measurement = tds.record(channel, options['-d'])
            measurements.append(measurement)
            if not (len(measurement['data']) == 2500):
                return channel
        if len(measurements) > 0:
            if options['-d']:
                filename = '{}.dat'.format(options['FILENAME'])
                with open(filename, 'w') as fileptr:
                    for i in range(2500):
                        line = '{}'.format(measurements[0]['t'][i])
                        for channel in measurements:
                            line += ' {}'.format(channel['data'][i])
                        fileptr.write(line + '\n')
            else:
                filename = '{}.yaml'.format(options['FILENAME'])
                with open(filename, 'w') as fileptr:
                    fileptr.write(yaml.dump(measurements))
    return 0

if __name__ == "__main__":
    ARGUMENTS = docopt(__doc__)
    if ARGUMENTS['-v']:
        print(ARGUMENTS)
    main(ARGUMENTS)
