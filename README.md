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

The Windows environment for Python is a bit messed up at this point in time.
The official Python releases for Windows and PyGobject for Windows have
diverged and use incompatible builds.  PyBluez, which requires the official
Python release build, cannot be used with a modern version of PyGobject,
which only builds on MSYS2 versions of Python.

To add insult to this, building binary packages on Windows for the official
Python builds require older, non-free versions of Microsoft compilers and
SDKs, many of which are not readily available unless one has an MSDN
subscription.

We're stuck with a compromise using really old versions of Python and
PyGObject.

Another issue is that PyBluez is no longer actively maintained.

Finally, the cx_Freeze module we rely on to create the MSI installer
appears to just grab all of the installed Gnome files and package them
in the binary, needed or not.  Essentially this grabs everything that
was installed by PyGObject.  This creates a rather large MSI file
filled with quite a lot of unneeded and unused content.  I have found
no way to exclude these.

----

With that out of the way, here is how to build and package this software
on Windows:

Install 64-bit Python 2.7.15 from here:
https://www.python.org/downloads/release/python-2715/1

Install pygobject3 for Windows from here:
https://sourceforge.net/projects/pygobjectwin32/files/pygi-aio-3.24.1_rev1-setup_049a323fe25432b10f7e9f543b74598d4be74a39.exe/download

Install cx_Freeze:
python -m pip install cx_Freeze

Install Visual Studio for Python 2.7:
https://www.microsoft.com/en-us/download/details.aspx?id=44266

This is needed to build PyBluez on Windows.

Install PyBluez:
python -m pip install PyBluez

The upgrade code is e6e4c96d-2b0a-4695-a754-efac18a2e923.  This allows packages
with the same code to replace older versions.  If you fork this code, please
change the UUID used for the upgrade code.

Execute the following to generate the Windows MSI for the package:
C:\Python27\python.exe setup.py bdist_msi --upgrade-code e6e4c96d-2b0a-4695-a754-efac18a2e923

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

