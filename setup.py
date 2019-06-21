#!/usr/bin/env python2.7

import os, site, sys

freeze = False
try:
    from cx_Freeze import setup, Executable
    freeze = True
except ImportError:
    from setuptools import setup

## Get the site-package folder, not everybody will install
## Python into C:\PythonXX
site_dir = site.getsitepackages()[1]
include_dll_path = os.path.join(site_dir, "gtk")

## Collect the list of missing dll when cx_freeze builds the app
missing_dll = ['libgtk-3-0.dll',
               'libgdk-3-0.dll',
               'libatk-1.0-0.dll',
               'libcairo-gobject-2.dll',
               'libgdk_pixbuf-2.0-0.dll',
               'libjpeg-8.dll',
               'libpango-1.0-0.dll',
               'libpangocairo-1.0-0.dll',
               'libpangoft2-1.0-0.dll',
               'libpangowin32-1.0-0.dll',
               'libpyglib-gi-2.0-python-0.dll',
               'libglib-2.0-0.dll',
               'libgobject-2.0-0.dll',
               'libintl-8.dll',
               'libgirepository-1.0-1.dll',
               'libgio-2.0-0.dll',
               'libgmodule-2.0-0.dll',
               'libffi-6.dll',
               'zlib1.dll',
               'libcairo-2.dll',
               'libfontconfig-1.dll',
               'libfreetype-6.dll',
               'libxml2-2.dll',
               'libpng15-15.dll',
               'libjson-glib-1.0-0.dll',
               'libgnutls-26.dll',
               'libgcrypt-11.dll',
               'libp11-kit-0.dll'
]

## We also need to add the glade folder, cx_freeze will walk
## into it and copy all the necessary files
glade_folder = 'glade'

## We need to add all the libraries too (for themes, etc..)
gtk_libs = ['etc', 'lib', 'share']

## Create the list of includes as cx_freeze likes
include_files = []
for dll in missing_dll:
    include_files.append((os.path.join(include_dll_path, dll), dll))

## Let's add glade folder and files
include_files.append((glade_folder, glade_folder))

## Let's add gtk libraries folders and files
for lib in gtk_libs:
    include_files.append((os.path.join(include_dll_path, lib), lib))

base = None

## Lets not open the console while running the app
if sys.platform == "win32":
    base = "Win32GUI"

if freeze:
    executables = [Executable("TncConfigApp.py", base=base)]
    scripts = None
else:
    scripts = ['TncConfigApp.py']
    executables = None

py_modules = ['Avr109', 'BootLoader', 'IntelHexRecord', 'TncModel']

buildOptions = dict(
    compressed = False,
    includes = ["gi"],
    packages = ["gi"],
    include_files = include_files
    )

setup(
    name = "TncConfigApp",
    version = "1.0.1",
    author = "Mobilinkd LLC",
    author_email = "mobilinkd@gmail.com",
    url = "https://github.com/mobilinkd/tnc1-python-config",
    license = "Apache 2.0",
    description = "Configuration tool for Mobilinkd TNC1, TNC2 and TNC3 (serial version)",
    long_description = 
"""This program is used to connect to a Mobilinkd TNC via Bluetooth SPP
(serial port) and is used to set the transmit volume level, monitor receive
volume level so it can be properly adjusted on the radio, set the KISS
parameters, and upload new firmware to the TNC.  It requires that the TNC has
been connected to the computer and assigned a serial port.""",
    options = dict(build_exe = buildOptions),
    platforms = ('Any',),
    keywords = ('mobilinkd', 'aprs', 'ham', 'afsk', 'tnc', 'ax25', 'kiss'),
    requires = ['pyserial', 'pygobject3'],
    executables = executables,
    scripts = scripts,
    py_modules = py_modules,
    data_files = [
        ('share/TncConfigApp/glade', ['glade/TncConfigApp.glade', 'glade/TncConfigApp.css']),
        ('share/TncConfigApp/glade/images', ['glade/images/Logo.png']),
        ('share/doc/TncConfigApp', ['LICENSE', 'README.md'])]
)

