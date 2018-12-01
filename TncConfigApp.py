#!/usr/bin/env python3

import sys
import os
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk,GdkPixbuf,GObject,Pango,Gdk,Notify

import serial.tools.list_ports
import glob

from TncModel import TncModel

def comports():
    if os.name == 'posix':
        devices = serial.tools.list_ports.comports() + [(d,d,d) for d in glob.glob('/dev/rfcomm*')]
        return devices
    else:
        return serial.tools.list_ports.comports()

def glade_location():

    bin_path = os.path.abspath(os.path.dirname(sys.argv[0]))

    if bin_path in ["/usr/bin", "/bin"]:
        share_path = '/usr/share/MobilinkdTnc1Config'
    else:
        share_path = bin_path
    
    return share_path

        
class TncConfigApp(object):

    def __init__(self):
        self.tnc = None
        self.device_path = None
        self.connect_message = None
        
        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(glade_location(), "glade/TncConfigApp.glade"))
        
        self.main_window = self.builder.get_object("main_window")
        self.main_window.connect("delete-event", self.close)

        self.init_serial_port_combobox()
        self.init_audio_input_frame()
        self.init_audio_output_frame()
        self.init_power_settings_frame()
        self.init_kiss_parameters_frame()
        self.init_modem_settings_frame()
        self.init_tnc_information_frame()
        self.init_update_firmware_frame()
        self.init_save_settings_frame()

        self.builder.connect_signals(self)

        self.main_window.show()
        # Notify.init("App Name")
        # Notify.Notification.new("Hi").show()
        Gtk.main()
    
    def __del__(self):
        
        Notify.uninit()
    
    def close(self, widget, data=None):
    
        if self.tnc is not None:
            self.tnc.disconnect()
            self.tnc = None
        Gtk.main_quit()

    def init_serial_port_combobox(self):
        self.serial_port_combo_box_text = self.builder.get_object("serial_port_combo_box_text")
        assert(self.serial_port_combo_box_text is not None)
        for port in comports():
            self.serial_port_combo_box_text.append_text(port[0])
        
    def init_audio_input_frame(self):
        pass
    
    def init_audio_output_frame(self):
        pass
    
    def init_power_settings_frame(self):
        pass
    
    def init_kiss_parameters_frame(self):
        pass
    
    def init_modem_settings_frame(self):
        pass
    
    def init_tnc_information_frame(self):
        pass
    
    def init_update_firmware_frame(self):
        pass
    
    def init_save_settings_frame(self):
        pass
    
        
    def on_connect_button_toggled(self, widget):
    
        self.tnc = TncModel(self, self.device_path)
            
    
    def on_serial_port_combo_box_changed(self, widget, data = None):
        
        self.device_path = widget.get_active_text()
        
    
    def on_input_auto_adjust_button_clicked(self, widget):
        
        pass
    
    def on_input_twist_adjustment_changed(self, widget):
        
        pass
    
    def on_input_gain_adjustment_changed(self, widget):
        
        pass
    
    def on_input_gain_adjustment_value_changed(self, widget):
        
        pass
    

if __name__ == '__main__':

    GObject.threads_init()
    app = TncConfigApp()

