#!/usr/bin/python3
"""Simple GUI for getting data or hardcopy from a TDS oscilloscope.

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
    tdsgui.py (-h | --help)
    tdsgui.py [-hv] [--port=PORT] [--baud=BAUD] [--timeout=TIMEOUT]
              [--tdscli=TDSCLI]

Arguments:
    FILENAME  Body of the output file name: a hardcopy will be name
              <filename>.png, channel data will be named <filename>.yaml
              or <filename>.dat, respectively.
Options:
    -h                  Print this help message.
    -v                  Print status messages.
    --port=PORT         Serial communication port [default: /dev/ttyS0].
    --baud=BAUD         Symbol rate. Maximum of 19200 Bd unfortunately does not
                        seem to work [default: 9600].
    --timeout=TIMEOUT   Timeout value in seconds for waiting on oscilloscope
                        response [default: 3]
    --tdscli=TDSCLI     Path to command line interface [default: ./tds.py]
"""

import os
import time
from tkinter import Tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import Button
from docopt import docopt


def about():
    """Show license information."""
    messagebox.showinfo("About", "Copyright (C) 2013 Sönke Carstens-Behrens\n\
(carstens-behrens AT rheinahrcampus.de)\n\
This program is free software: you can redistribute it and/or \
modify it under the terms of the GNU General Public License as \
published by the Free Software Foundation, either version 3 of the \
License, or (at your option) any later version.\n\
This program is distributed in the hope that it will be useful, \
but WITHOUT ANY WARRANTY; without even the implied warranty of \
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU \
General Public License for more details.\n\
You should have received a copy of the GNU General Public License \
along with this program. If not, see \
<http://www.gnu.org/licenses/>.")


class Tdsgui:
    """Simple GUI"""
    def __init__(self, root, options):
        self.root = root
        self.options = options
        self.hardcopybutton = Button(self.root,
                text="Hardcopy", width=20, command=self.hardcopy)
        self.channel1button = Button(self.root,
                text="Import Channel 1", width=20, command=self.record1)
        self.channel2button = Button(self.root,
                text="Import Channel 2", width=20, command=self.record2)
        self.aboutbutton = Button(self.root,
                text="About", width=20, command=about)
        self.quitbutton = Button(self.root,
                text="Quit", width=20, command=self.quit)
        self.hardcopybutton.pack()
        self.channel1button.pack()
        self.channel2button.pack()
        self.aboutbutton.pack()
        self.quitbutton.pack()

    def hardcopy(self):
        """Get a hardcopy."""
        filename = filedialog.SaveAs(
                filetypes=[('PNG-Dateien', '*.png')],
                initialfile='hardcopy.png',
                title='Dateiname (Hardcopy)').show()
        if not filename:
            return
        filename = os.path.splitext(filename)[0]
        success = self.call_tds('--hardcopy {}'.format(filename))
        if not success:
            messagebox.showerror(
                    'Fehler',
                    'Zugriff auf Oszilloskop ist fehlgeschlagen!')
        else:
            os.system(
                    "montage -frame 4 -geometry +0+0 -background White\
                            -label '{}' {}.png {}.png".format(
                                time.strftime('%H:%M:%S',
                                    time.localtime(time.time())),
                                filename, filename))
            os.system('display {}.png'.format(filename))

    def record1(self):
        """Record Channel 1"""
        self.record('1')

    def record2(self):
        """Record Channel 2"""
        self.record('2')

    def record(self, channel):
        """Record a channel of the oscilloscope by calling tds.py"""
        filename = filedialog.SaveAs(
                filetypes=[('Textdateien', '*.dat')],
                initialfile='signal.dat',
                title='Dateiname (Kanalaufnahme)').show()
        if filename:
            filename = os.path.splitext(filename)[0]
            success = self.call_tds('-d --channel={} {}'.format(
                channel, filename))
            if success:
                command = """echo "plot '{}' title 'Rohsignal' with lines " |\
                        gnuplot -persist -""".format(filename + '.dat')
                os.system(command)

    def call_tds(self, option):
        """Call command line tool."""
        command = '{} -v --port={} --baud={} {}'.format(
                self.options['--tdscli'],
                self.options['--port'],
                self.options['--baud'], option)
        print(command)
        success = os.system(command)
        if success == 0:
            return True
        else:
            return False

    def quit(self):
        """Destroy GUI, called from quit button or 'q' binding"""
        self.root.destroy()


def main(options):
    """Create GUI and perform interactions."""
    root = Tk()
    root.title('Oscilloscope GUI')
    gui = Tdsgui(root, options)
    print(type(gui))
    root.mainloop()

if __name__ == "__main__":
    ARGUMENTS = docopt(__doc__)
    if ARGUMENTS['-v']:
        print(ARGUMENTS)
    main(ARGUMENTS)
