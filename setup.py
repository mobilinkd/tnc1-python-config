#!/usr/bin/env python2.7

import os, site, sys, glob

freeze = False
try:
    from cx_Freeze import setup, Executable
    freeze = True
except ImportError:
    from setuptools import setup

## Get the site-package folder, not everybody will install
## Python into C:\PythonXX
site_dir = site.getsitepackages()[1]
include_dll_path = os.path.join(site_dir, "gnome")

## We also need to add the glade folder, cx_freeze will walk
## into it and copy all the necessary files
glade_folder = 'glade'

## We need to add all the libraries too (for themes, etc..)
gtk_libs = [
    'etc',
    'lib/gdbus-2.0',
    'lib/gdk-pixbuf-2.0',
    'lib/gio',
    'lib/girepository-1.0',
    'lib/glade',
    'lib/gtk-3.0',
    'share/dbus-1',
    'share/fontconfig',
    'share/fonts',
    'share/gir-1.0',
    'share/glade',
    'share/glib-2.0',
    'share/icons/Adwaita',
    'share/themes/Adwaita',
    # 'share/locale'
    ]

## Create the list of includes as cx_freeze likes
include_files = []

for dll in glob.glob(os.path.join(include_dll_path, "*.dll")):
    include_files.append((dll, os.path.basename(dll)))

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
    executables = [
        Executable(
            "TncConfigApp.py",
            base=base,
            shortcutName="Mobilinkd TNC Config",
            shortcutDir="StartMenuFolder"
    )]
    scripts = None
else:
    scripts = ['TncConfigApp.py']
    executables = None

py_modules = ['Avr109', 'BootLoader', 'IntelHexRecord', 'TncModel']

buildOptions = dict(
    includes = ["gi"],
    packages = ["gi"],
    include_files = include_files,
    )

setup(
    name = "TncConfigApp",
    version = "1.1.3",
    author = "Mobilinkd LLC",
    author_email = "mobilinkd@gmail.com",
    url = "https://github.com/mobilinkd/tnc1-python-config",
    license = "Apache 2.0",
    description = "Configuration tool for Mobilinkd TNC1, TNC2 and TNC3",
    long_description = 
"""This program is used to connect to a Mobilinkd TNC via RFCOMM only (not
serial port) and is used to set the transmit volume level, monitor receive
volume level so it can be properly adjusted on the radio, set the KISS
parameters, and upload new firmware to TNC1 & TNC2 devices.""",
    options = dict(build_exe = buildOptions),
    platforms = ('Any',),
    keywords = ('mobilinkd', 'aprs', 'ham', 'afsk', 'tnc', 'ax25', 'kiss'),
    requires = ['PyBluez', 'pygobject3'],
    executables = executables,
    scripts = scripts,
    py_modules = py_modules,
    data_files = [
        ('share/TncConfigApp/glade', ['glade/TncConfigApp.glade', 'glade/TncConfigApp.css']),
        ('share/TncConfigApp/glade/images', ['glade/images/Logo.png']),
        ('share/doc/TncConfigApp', ['LICENSE', 'README.md'])]
)

