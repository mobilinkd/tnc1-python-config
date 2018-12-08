tnc1-python-config
==================

Python package for configuring the Mobilinkd TNC.

This is a Windows and Linux GUI app written in Python, GTK+, GObject using
Glade.  Any help getting this to work on Apple OSX would be most welcome.

It allows one to monitor the input volume, adjust the output volume, and set
the KISS parameters of the Mobilinkd TNC.

The firmware upload portion is now complete.  The bootloader on the TNC is
XBoot++, an AVR109 (butterfly) style bootloader.  Please see the AVR109 spec
and sample code from Atmel, along with the avrdude source, for details
on the bootloader protocol.

This package has dependencies on pygobject3, pyserial and, on Windows,
cx_freeze.

Windows Build
=============

*** Windows builds currently must be 32-bit due to PyGObject ***

Read this for background on pygobject: https://wiki.gnome.org/PyGObject

Install 32-bit Python 2.7.5 from here: http://www.python.org/getit/

pygobject3 on Windows is only packaged for 32-bit installs.

Install pygobject3 for Windows from here:
https://code.google.com/p/osspack32/downloads/detail?name=pygi-aio-3.4.2rev11.7z&can=2&q=/

Make sure you follow the installation instructions in the README.
Importantly, the top-level gtk directory needs to be copied over the py27/gtk
directory.

Install cx_freeze for 32-bit Python 2.7 from SourceForge:
http://sourceforge.net/projects/cx-freeze/files/4.3.2/cx_Freeze-4.3.2.win32-py2.7.msi/download

Install pip-Win by installing and executing this package:
https://bitbucket.org/pcarbonn/pipwin/downloads/pip-Win_1.6.exe

Using pip-Win to install pyserial.

Execute the following to generate the Windows MSI for the package:
C:\Python27\python.exe setup.py bdist_msi

Linux Build
===========

This was built/tested with Python 3.6, pyserial-3.1.1 and pygobject-3.28.3

python3-3.6.6-1.fc28.x86_64
python3-pyserial-3.1.1-6.fc28.noarch
python3-gobject-3.28.3-1.fc28.x86_64

./setup.py bdist_rpm

Will build an RPM that can be installed.

OS X Build
===========

You will need the X11 server installed from here: https://xquartz.macosforge.org/landing/

Using brew

brew install python3 (upgrade to python-3.7)
pip3.7 install pyserial
brew install gtk+3
brew install pygobject3
brew install libnotify
brew install gnome-icon-theme

/opt/local/bin/python3.7 TncConfigApp.py

