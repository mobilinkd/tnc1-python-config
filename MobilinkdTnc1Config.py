#!/usr/bin/env python2.7

import sys
import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GdkPixbuf,GObject,Pango,Gdk

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

class MobilinkdTnc1Config(object):

    def __init__(self):
        self.tnc = None
        self.connect_message = None
        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(glade_location(), "glade/MobilinkdTnc1Config.glade"))
        
        self.window = self.builder.get_object("window")
        self.window.connect("delete-event", self.close)
        
        self.init_serial_port_combobox()
        self.init_power_section()
        self.init_transmit_volume()
        self.init_receive_volume()
        self.init_kiss_parameters()
        self.init_firmware_section()
        self.init_eeprom_section()
        
        self.status = self.builder.get_object("statusbar")
        self.builder.connect_signals(self)

        self.tnc_disconnect()

        self.window.show()
        Gtk.main()
    
    def close(self, widget, data=None):
    
        if self.tnc is not None:
            self.tnc.disconnect()
            self.tnc = None
        Gtk.main_quit()

    def init_serial_port_combobox(self):
        self.serial_port_combobox = self.builder.get_object("serial_port_combobox")
        for port in comports():
            self.serial_port_combobox.append_text(port[0])
    
    def on_serial_port_combobox_changed(self, widget, data=None):
        text = widget.get_active_text()
        if text != None:
            self.tnc = TncModel(self, text)
    
    def init_power_section(self):
        self.battery_level_label = self.builder.get_object("battery_level_label")
        self.battery_level_bar = self.builder.get_object("battery_level_bar")
        self.battery_level_bar.set_fraction(0.0)
     
        self.power_control_box = self.builder.get_object("power_control_box")
        self.usb_on_button = self.builder.get_object("usb_on_button")
        self.usb_off_button = self.builder.get_object("usb_off_button")
        self.usb_on_button.set_sensitive(False)
        self.usb_off_button.set_sensitive(False)
    
    def init_eeprom_section(self):
        self.eeprom_frame = self.builder.get_object("eeprom_frame")
        self.eeprom_save_button = self.builder.get_object("eeprom_save_button")
        self.eeprom_save_button.set_sensitive(False)
        self.eeprom_frame.set_visible(False)
    
    def init_transmit_volume(self):
    
        self.transmit_volume_scale = self.builder.get_object("transmit_volume_scale")
        self.transmit_volume_scale.set_range(16.0, 255.0)
        self.transmit_volume_scale.set_value(128.0)
        self.transmit_volume_scale.set_sensitive(False)
        
        self.mark_toggle_button = self.builder.get_object("mark_toggle_button")
        self.space_toggle_button = self.builder.get_object("space_toggle_button")
        self.ptt_toggle_button = self.builder.get_object("ptt_toggle_button")
    
    def on_mark_toggle_button_toggled(self, widget, data=None):
        self.tnc.set_mark(widget.get_active())
    
    def on_space_toggle_button_toggled(self, widget, data=None):
        self.tnc.set_space(widget.get_active())
    
    def on_ptt_toggle_button_toggled(self, widget, data=None):
        self.tnc.set_ptt(widget.get_active())
    
    def on_input_atten_toggle_button_toggled(self, widget, data=None):
        self.tnc.set_input_atten(widget.get_active())
    
    def on_transmit_volume_scale_change_value(self, widget, scroll, value, data=None):
        if value > 255: value = 255
        if value < 0: value = 0
        widget.set_value(int(value))
        self.tnc.set_tx_volume(int(value))
        return True

    def init_receive_volume(self):
        self.receive_volume_levelbar = self.builder.get_object("receive_volume_levelbar")
        self.receive_volume_levelbar.add_offset_value(Gtk.LEVEL_BAR_OFFSET_LOW, 5.0)
        self.receive_volume_levelbar.add_offset_value(Gtk.LEVEL_BAR_OFFSET_HIGH, 7.0)
        self.receive_volume_levelbar.set_value(0.0)
        self.input_atten_toggle_button = self.builder.get_object("input_atten_toggle_button")

        self.receive_volume_progressbar = self.builder.get_object("receive_volume_progressbar")

        if os.name != "posix":
            self.receive_volume_progressbar.show()
            self.receive_volume_levelbar.hide()
            self.receive_volume_progressbar.set_fraction(0.0)

    def init_kiss_parameters(self):
        self.dcd_toggle_button = self.builder.get_object("dcd_toggle_button")
        self.kiss_tx_delay_spin_button = self.builder.get_object("kiss_tx_delay_spin_button")
        self.kiss_tx_delay_spin_button.set_range(0.0, 255.0)
        self.kiss_tx_delay_spin_button.set_increments(1.0, 10.0)
        self.kiss_tx_delay_spin_button.set_value(50)
        self.kiss_persistence_spin_button = self.builder.get_object("kiss_persistence_spin_button")
        self.kiss_persistence_spin_button.set_range(0.0, 255.0)
        self.kiss_persistence_spin_button.set_increments(1.0, 10.0)
        self.kiss_persistence_spin_button.set_value(63)
        self.kiss_slot_time_spin_button = self.builder.get_object("kiss_slot_time_spin_button")
        self.kiss_slot_time_spin_button.set_range(0.0, 255.0)
        self.kiss_slot_time_spin_button.set_increments(1.0, 10.0)
        self.kiss_slot_time_spin_button.set_value(25)
        self.kiss_tx_tail_spin_button = self.builder.get_object("kiss_tx_tail_spin_button")
        self.kiss_tx_tail_spin_button.set_range(0.0, 255.0)
        self.kiss_tx_tail_spin_button.set_increments(1.0, 10.0)
        self.kiss_tx_tail_spin_button.set_value(2)
        self.kiss_duplex_toggle_button = self.builder.get_object("kiss_duplex_toggle_button")
        self.kiss_full_duplex_image = self.builder.get_object("kiss_full_duplex_image")
        self.kiss_half_duplex_image = self.builder.get_object("kiss_half_duplex_image")
        self.conn_track_toggle_button = self.builder.get_object("conn_track_toggle_button")
        self.verbose_toggle_button = self.builder.get_object("verbose_toggle_button")
        self.ptt_label = self.builder.get_object("ptt_label")
        self.ptt_simplex_radiobutton = self.builder.get_object("ptt_simplex_radiobutton")
        self.ptt_multiplex_radiobutton = self.builder.get_object("ptt_multiplex_radiobutton")
    
    def on_dcd_toggled(self, widget, data=None):
        self.tnc.set_squelch_level((not widget.get_active()) * 2)
    
    def on_ptt_toggled(self, widget, data=None):
        if widget.get_active():
            self.tnc.set_ptt_channel(self.ptt_multiplex_radiobutton.get_active())
    
    def on_verbose_toggled(self, widget, data=None):
        self.tnc.set_verbosity(widget.get_active())
    
    def on_kiss_duplex_toggled(self, widget, data=None):
        self.tnc.set_duplex(widget.get_active())
    
    def on_conn_track_toggled(self, widget, data=None):
        self.tnc.set_conn_track(widget.get_active())
    
    def on_kiss_tx_delay_spin_button_value_changed(self, widget, data=None):
        self.tnc.set_tx_delay(widget.get_value_as_int())
        
    def on_kiss_persistence_spin_button_value_changed(self, widget, data=None):
        self.tnc.set_persistence(widget.get_value_as_int())
        
    def on_kiss_slot_time_spin_button_value_changed(self, widget, data=None):
        self.tnc.set_time_slot(widget.get_value_as_int())
        
    def on_kiss_tx_tail_spin_button_value_changed(self, widget, data=None):
        self.tnc.set_tx_tail(widget.get_value_as_int())
        
    def on_connect_button_clicked(self, widget, data=None):
        if self.tnc is None:
            self.connect_message = self.status.push(1, "Please choose a serial port.")
            return
            
        if self.tnc.connected():
            self.connect_message = self.status.push(1, "Already connected.")
            return
        
        if self.connect_message is not None:
            self.status.remove(1, self.connect_message)
        self.tnc.connect()

    def on_window_destroy(self, widget, data=None):
        print "quitting"
        Gtk.main_quit()
    
    def init_firmware_section(self):
    
        self.firmware_file_chooser_button = self.builder.get_object("firmware_file_chooser_button")
        self.upload_button = self.builder.get_object("upload_button")
        self.firmware_entry = self.builder.get_object("firmware_entry")
    
    def on_firmware_file_chooser_button_file_set(self, widget, data=None):
        self.firmware_file = self.firmware_file_chooser_button.get_filename()
        self.upload_button.set_sensitive(True)
        
    def on_eeprom_save_button_clicked(self, widget, data=None):
        self.tnc.save_eeprom_settings()
    
    def on_usb_on_button_toggled(self, widget, data=None):
        self.tnc.set_usb_on(widget.get_active())
    
    def on_usb_off_button_toggled(self, widget, data=None):
        self.tnc.set_usb_off(widget.get_active())
    
    def on_upload_button_clicked(self, widget, data=None):
        self.firmware_gui = FirmwareUploadGui(self.builder, self.tnc)
        self.tnc.upload_firmware(self.firmware_file, self.firmware_gui)
        self.firmware_gui_tag = GObject.idle_add(self.check_firmware_upload_complete)
    
    def tnc_connect(self):
        self.serial_port_combobox.set_sensitive(False)
        self.transmit_volume_scale.set_sensitive(True)
        self.mark_toggle_button.set_sensitive(True)
        self.mark_toggle_button.set_active(False)
        self.space_toggle_button.set_sensitive(True)
        self.space_toggle_button.set_active(False)
        self.ptt_toggle_button.set_sensitive(True)
        self.ptt_toggle_button.set_active(False)
        
        self.dcd_toggle_button.set_sensitive(False)
        self.dcd_toggle_button.set_active(False)
        
        self.verbose_toggle_button.set_sensitive(False)
        self.verbose_toggle_button.set_active(False)
        
        self.kiss_tx_delay_spin_button.set_sensitive(True)
        
        self.kiss_persistence_spin_button.set_sensitive(True)
        self.kiss_slot_time_spin_button.set_sensitive(True)
        self.kiss_tx_tail_spin_button.set_sensitive(True)
        
        self.kiss_duplex_toggle_button.set_sensitive(False)
        self.kiss_duplex_toggle_button.set_active(False)
        
        self.conn_track_toggle_button.set_sensitive(False)
        self.conn_track_toggle_button.set_active(False)

        self.firmware_file_chooser_button.set_sensitive(True)
        self.upload_button.set_sensitive(False)
        self.firmware_entry.set_sensitive(True)
        
        
    def tnc_disconnect(self):
        self.transmit_volume_scale.set_sensitive(False)
        self.mark_toggle_button.set_sensitive(False)
        self.space_toggle_button.set_sensitive(False)
        self.ptt_toggle_button.set_sensitive(False)
        self.ptt_simplex_radiobutton.set_sensitive(False)
        self.ptt_multiplex_radiobutton.set_sensitive(False)
        
        self.dcd_toggle_button.set_sensitive(False)
        self.kiss_tx_delay_spin_button.set_sensitive(False)
        self.kiss_persistence_spin_button.set_sensitive(False)
        self.kiss_slot_time_spin_button.set_sensitive(False)
        self.kiss_tx_tail_spin_button.set_sensitive(False)
        self.kiss_duplex_toggle_button.set_sensitive(False)
        self.conn_track_toggle_button.set_sensitive(False)
            
        self.firmware_file_chooser_button.set_sensitive(False)
        self.upload_button.set_sensitive(False)
        self.firmware_entry.set_sensitive(False)
        
        self.usb_on_button.set_sensitive(False)
        self.usb_off_button.set_sensitive(False)

    def tnc_rx_volume(self, value):
        self.receive_volume_levelbar.set_value(value)
        self.receive_volume_progressbar.set_fraction(value / 8.0)
        
    def tnc_tx_volume(self, value):
        self.transmit_volume_scale.set_value(value)
    
    def tnc_battery_level(self, value):
        self.battery_level_label.set_text(str(int(value)) + "mV")
        level = (value - 3400.0) / 100.0
        self.battery_level_bar.set_fraction(level / 8.0)
    
    def tnc_power_on(self, value):
        self.usb_on_button.set_sensitive(True)
        self.usb_on_button.set_active(value)

    def tnc_power_off(self, value):
        self.usb_off_button.set_sensitive(True)
        self.usb_off_button.set_active(value)

    def tnc_input_atten(self, value):
        self.input_atten_toggle_button.set_active(value > 0);
        
    def tnc_squelch_level(self, value):
        pass
    
    def tnc_tx_delay(self, value):
        self.kiss_tx_delay_spin_button.set_value(value)
    
    def tnc_persistence(self, value):
        self.kiss_persistence_spin_button.set_value(value)
    
    def tnc_slot_time(self, value):
        self.kiss_slot_time_spin_button.set_value(value)
    
    def tnc_tx_tail(self, value):
        self.kiss_tx_tail_spin_button.set_value(value)
    
    def tnc_dcd(self, value):
        self.dcd_toggle_button.set_sensitive(True)
        self.dcd_toggle_button.set_active(value == 0)
    
    def tnc_verbose(self, value):
        self.verbose_toggle_button.set_sensitive(True)
        self.verbose_toggle_button.set_active(value)
    
    def tnc_duplex(self, value):
        self.kiss_duplex_toggle_button.set_sensitive(True)
        self.kiss_duplex_toggle_button.set_active(value)
        return
        if value:
            self.kiss_duplex_toggle_button.set_image(self.kiss_full_duplex_image)
        else:
            self.kiss_duplex_toggle_button.set_image(self.kiss_half_duplex_image)
    
    def tnc_conn_track(self, value):
        self.conn_track_toggle_button.set_sensitive(True)
        self.conn_track_toggle_button.set_active(value)
    
    def tnc_eeprom_save(self):
        self.eeprom_frame.set_visible(True)
        self.eeprom_save_button.set_sensitive(True)
    
    def tnc_firmware_version(self, value):
        self.firmware_entry.set_text(value)

    def tnc_ptt_style(self, value):
        
        self.ptt_label.set_visible(True)
        self.ptt_simplex_radiobutton.set_visible(True)
        self.ptt_multiplex_radiobutton.set_visible(True)
        
        self.ptt_simplex_radiobutton.set_sensitive(True)
        self.ptt_simplex_radiobutton.set_active(False)
        
        self.ptt_multiplex_radiobutton.set_sensitive(True)
        self.ptt_multiplex_radiobutton.set_active(False)
        
        if value == 0:
            self.ptt_simplex_radiobutton.set_active(True)
        else:
            self.ptt_multiplex_radiobutton.set_active(True)
    
    def exception(self, e):
        context = self.status.get_context_id("exception")
        self.status.pop(context)
        self.status.push(context, str(e))
        # dialog = self.builder.get_object("error_dialog")
        # dialog.format_secondary_text(str(e))
        # dialog.run()
        # dialog.hide()
    
    def notice(self, msg):
        context = self.status.get_context_id("notice")
        self.status.pop(context)
        self.status.push(context, msg)
        pass
        
    def check_firmware_upload_complete(self):
        
        assert(self.firmware_gui is not None)
        if not self.firmware_gui.complete():
            self.firmware_gui_tag = GObject.idle_add(self.check_firmware_upload_complete)
            return
        
        self.tnc.upload_firmware_complete()
        self.firmware_gui.dialog()
        self.firmware_gui = None
        # Gtk.main_quit()
        

def replace_widget(current, new):
    """Replace one widget with another.
    'current' has to be inside a container (e.g. gtk.VBox).
    """
    container = current.get_parent()
    assert container # is "current" inside a container widget?

    Gtk.Container.remove(container, current)
    container.add(new)
    

class FirmwareUploadGui(object):
    
    def __init__(self, builder, tnc):
        
        self.builder = builder
        self.tnc = tnc
        self.statusbar = self.builder.get_object("statusbar")
        self.progressbar = self.builder.get_object("firmware_progress_bar")
        self.success_dialog = self.builder.get_object("firmware_success_dialog")
        self.error_dialog = self.builder.get_object("firmware_error_dialog")
        replace_widget(self.statusbar, self.progressbar)
        self.result = None
    
    def __del__(self):
        
        replace_widget(self.progressbar,self.statusbar)
    
    def complete(self):
    
        return self.result is not None
    
    def set_steps(self, steps):
        
        self.progressbar.set_pulse_step(1.0 / steps)

    def writing(self):
        
        self.progressbar.set_text("Writing...")
        self.progressbar.set_fraction(0.0)
    
    def verifying(self):
        
        self.progressbar.set_text("Verifying...")
        self.progressbar.set_fraction(0.0)
    
    def pulse(self):
        
        self.progressbar.pulse()
    
    def success(self):
        
        self.result = self.success_dialog
    
    def failure(self, msg):
        
        self.error_dialog.format_secondary_text(msg)
        self.result = self.error_dialog

    def dialog(self):
        
        self.result.run()
        self.result.hide()
        # self.success_dialog.hide()


if __name__ == '__main__':

    GObject.threads_init()
    app = MobilinkdTnc1Config()

