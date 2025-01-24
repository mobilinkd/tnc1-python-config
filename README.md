# tnc1-python-config

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

# Windows Build

Install 64-bit Python 2.7.15 from here:
https://www.python.org/downloads/release/python-2715/1

Install pygobject3 for Windows from here:
https://sourceforge.net/projects/pygobjectwin32/files/pygi-aio-3.24.1_rev1-setup_049a323fe25432b10f7e9f543b74598d4be74a39.exe/download

Install cx_Freeze:
python -m pip install cx_Freeze

Install pyserial:
python -m pip install pyserial

Execute the following to generate the Windows MSI for the package:
python setup.py bdist_msi --upgrade-code e6e4c96d-2b0b-4695-a754-efac18a2e923


# Linux Build


## Fedora / Red Hat / Other RPM-based systems

This was built/tested with Python 3.6, pyserial-3.1.1 and pygobject-3.28.3

python3-3.6.6-1.fc28.x86_64
python3-pyserial-3.1.1-6.fc28.noarch
python3-gobject-3.28.3-1.fc28.x86_64

    ./setup.py bdist_rpm 

Will build an RPM that can be installed.

## Debian/Ubuntu

I have not managed to build a working deb package. The dependecies are never
properly listed or handled.

However, it will build a package and install it. If the dependencies are satisfied,
the application will work. Here are the runtime dependencies:

    sudo apt-get install python-gobject python3-serial gir1.2-notify-0.7

And this is the build process:

    sudo apt-get install python-stdeb python3-stdeb python-all python3-all dh-python fakeroot 
    python3 ./setup.py --command-packages=stdeb.command bdist_deb

This was confirmed on a Raspberry Pi running Ubuntu 20.04.6 LTS.

# OS X Build

You will need the X11 server installed from here: https://xquartz.macosforge.org/landing/

Using brew

brew install python3 (upgrade to python-3.7)
pip3.7 install pyserial
brew install gtk+3
brew install pygobject3
brew install libnotify
brew install gnome-icon-theme

/opt/local/bin/python3.7 TncConfigApp.py

