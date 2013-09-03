tnc1-python-config
==================

Python package for configuring the Mobilinkd TNC.

This is a Windows and Linux GUI app written in Python, GTK+, GObject using
Glade.

It allows one to monitor the input volume, adjust the output volume, and set
the KISS parameters of the Mobilinkd TNC.  There are a few items that are not
still working: 1200Hz tone, DCD, and firmware upload.

The firmware upload portion is a work in progress.  The bootloader on the TNC
is an AVR109 (butterfly) style bootloader.  The parts that are in there have
been cribbed from the avrdude source code.

This package has dependencies on pygobject3, pyserial and, on Windows,
cx_freeze.

Windows Build
=============

Read this for background on pygobject: https://wiki.gnome.org/PyGObject

Install 32-bit Python 2.7.5 from here: http://www.python.org/getit/

pygobject3 on Windows is only packaged for 32-bit installs.

Install pygobject3 for Windows from here:
https://code.google.com/p/osspack32/downloads/detail?name=pygi-aio-3.4.2rev11.7z&can=2&q=/

Make sure you follow the installation instructions in the README.
Importantly, the top-level gtk directory needs to be copied over the py27/gtk
directory.

Install pip-Win by installing and executing this package:
https://bitbucket.org/pcarbonn/pipwin/downloads/pip-Win_1.6.exe

Using pip-Win to install pyserial.

Execute the following to generate the Windows MSI for the package:
C:\Python27\python.exe setup.py bdist_msi

Linux Build
===========

This was build with Python 2.7.5, pyserial-2.6.4 and pygobject-3.8.3

./setup.py bdist_rpm

Will build an RPM that can be installed.


