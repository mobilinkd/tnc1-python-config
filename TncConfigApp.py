#!/usr/bin/env python3

import sys
import os
import gi
import time

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk,GdkPixbuf,GObject,Pango,Gdk,Notify

import serial.tools.list_ports

from TncModel import TncModel

def glade_location():

    bin_path = os.path.abspath(os.path.dirname(sys.argv[0]))

    if bin_path in ["/usr/bin", "/bin"]:
        share_path = '/usr/share/TncConfigApp'
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
        
        # settings = Gtk.Settings.get_default()
        # settings.set_property("gtk-font-name", "Cantarell")
        # settings.set_property("gtk-icon-theme-name", "Oxygen")

        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_path(os.path.join(glade_location(), 'glade/TncConfigApp.css'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            cssProvider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.main_window = self.builder.get_object("main_window")
        self.main_window.connect("delete-event", self.close)

        self.stack = self.builder.get_object("config_stack")
        self.stack.set_sensitive(False)
        self.sidebar = self.builder.get_object("config_sidebar")
        self.sidebar.set_sensitive(False)

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
         
        self.visible_frame=None
        self.change_visible_frame('audio_input')

        Notify.init("TncConfigApp")
        Gtk.main()

    def __del__(self):
        
        Notify.uninit()
    
    def close(self, widget, data=None):
    
        if self.tnc is not None:
            self.tnc.disconnect()
            self.tnc = None
        Gtk.main_quit()


    def need_save(self):
        pass

    ### Main UI Section
    
    def init_serial_port_combobox(self):
        self.connect_button = self.builder.get_object("connect_button")
        self.connect_button.set_sensitive(False)
        self.serial_port_combo_box_text = self.builder.get_object("serial_port_combo_box_text")
        assert(self.serial_port_combo_box_text is not None)
        for port in serial.tools.list_ports.comports():
            self.serial_port_combo_box_text.append_text(port[0])
        
    def on_connect_button_toggled(self, widget):
    
        if widget.get_active():
            self.tnc = TncModel(self, self.device_path)
            self.tnc.connect()
        elif self.tnc is not None:   # Possible race condition here...
            self.tnc.disconnect()
            self.tnc = None
            
    
    def on_serial_port_combo_box_changed(self, widget, data = None):
        
        self.device_path = widget.get_active_text()
        self.connect_button.set_sensitive(True)
    
    ### GtkStack
    def on_config_stack_visible_child_name_notify(self, widget, param):
        print("visible-child-name", widget.get_visible_child_name())
        self.change_visible_frame(widget.get_visible_child_name())
    
    def leave_frame(self, widget_name):
        """Dynamic dispatch to on_*_leave() function"""
        getattr(self, "on_" + widget_name + "_leave")()
    
    def enter_frame(self, widget_name):
        """Dynamic dispatch to on_*_enter() function"""
        getattr(self, "on_" + widget_name + "_enter")()
    
    def change_visible_frame(self, name):
    
        if self.visible_frame == name: return
        if self.visible_frame is not None:
            self.leave_frame(self.visible_frame)
        self.visible_frame = name
        self.enter_frame(self.visible_frame)
    
    ### Audio Input...
    def init_audio_input_frame(self):
        self.audio_input_frame = self.builder.get_object("audio_input_frame")
        
        self.audio_input_level_bar = self.builder.get_object("audio_input_level_bar")
        self.audio_input_level_bar.add_offset_value("audio_input_level_bar-high", 10);
        self.audio_input_level_bar.add_offset_value("audio_input_level_bar-medium", 8);
        self.audio_input_level_bar.add_offset_value("audio_input_level_bar-low", 6);
        
        self.input_attenuation_box = self.builder.get_object("input_attenuation_box")
        self.input_attenuation_box.set_visible(False)
        self.input_attenuation_check_button = self.builder.get_object("input_attenuation_check_button")
        
        self.input_gain_box = self.builder.get_object("input_gain_box")
        self.input_gain_box.set_visible(False)
        self.input_gain_scale = self.builder.get_object("input_gain_scale")
        self.input_gain_min_label = self.builder.get_object("input_gain_min_label")
        self.input_gain_max_label = self.builder.get_object("input_gain_max_label")
        
        self.input_twist_box = self.builder.get_object("input_twist_box")
        self.input_twist_box.set_visible(False)
        self.input_twist_scale = self.builder.get_object("input_twist_scale")
        self.input_twist_min_label = self.builder.get_object("input_twist_min_label")
        self.input_twist_max_label = self.builder.get_object("input_twist_max_label")
        
        self.input_auto_adjust_button = self.builder.get_object("input_auto_adjust_button")
        self.input_auto_adjust_button.set_visible(False)
        
        self.last_audio_input_update_time = time.time()

    
    def on_audio_input_enter(self):
        self.last_audio_input_update_time = 0
        if self.tnc is not None:
            self.tnc.stream_audio_on()
        
    def on_audio_input_leave(self):
        print('on_audio_input_leave')
        if self.tnc is not None:
            self.tnc.stream_audio_off()
    
    def on_input_attenuation_check_button_toggled(self, widget):
        self.tnc.set_input_atten(widget.get_active())
        self.tnc.stream_audio_on()
    
    def on_input_gain_adjustment_value_changed(self, widget):
        now = time.time()
        if now - self.last_audio_input_update_time > 0.1:
            self.tnc.set_input_gain(int(widget.get_value()))
            self.last_audio_input_update_time = now
            
    def on_input_gain_scale_button_release_event(self, widget, data = None):
        self.tnc.set_input_gain(int(widget.get_value()))
        self.last_audio_input_update_time = time.time()
    
    def on_input_twist_adjustment_value_changed(self, widget):
        now = time.time()
        if now - self.last_audio_input_update_time > 0.1:
            self.tnc.set_input_twist(int(widget.get_value()))
            self.last_audio_input_update_time = now
    
    def on_input_twist_scale_button_release_event(self, widget, event, data = None):
        self.tnc.set_input_twist(int(widget.get_value()))
        self.last_audio_input_update_time = time.time()
    
    def on_input_auto_adjust_button_clicked(self, widget):
        self.tnc.adjust_input()

    
    ### Audio Output...
    def init_audio_output_frame(self):
        self.audio_output_frame = self.builder.get_object("audio_output_frame")
        
        self.ptt_style_box = self.builder.get_object("ptt_style_box")
        self.ptt_style_box.set_visible(False)
        self.ptt_simplex_radio_button = self.builder.get_object("ptt_simplex_radio_button")
        self.ptt_multiplex_radio_button = self.builder.get_object("ptt_multiplex_radio_button")
        
        self.output_gain_scale = self.builder.get_object("output_gain_scale")
        
        self.output_twist_box = self.builder.get_object("output_twist_box")
        self.output_twist_box.set_visible(False)
        self.output_twist_scale = self.builder.get_object("output_twist_scale")
        
        self.mark_tone_radio_button = self.builder.get_object("mark_tone_radio_button")
        self.space_tone_radio_button = self.builder.get_object("space_tone_radio_button")
        self.both_tone_radio_button = self.builder.get_object("both_tone_radio_button")
        self.transmit_toggle_button = self.builder.get_object("transmit_toggle_button")
        
        self.last_audio_output_update_time = time.time()
    
    def on_audio_output_enter(self):
        print('on_audio_output_enter')
        
    def on_audio_output_leave(self):
        print('on_audio_output_leave')
        
    def on_ptt_simplex_radio_button_toggled(self, widget):
        if self.tnc is None:
            return

        self.tnc.set_ptt_channel(self.ptt_multiplex_radio_button.get_active())
        
        self.need_save()
            
    def on_ptt_multiplex_radio_button_toggled(self, widget):
        """Do not need to check both simplex and multiplex buttons"""
        pass
    
    def on_output_gain_adjustment_value_changed(self, widget):
        now = time.time()
        if now - self.last_audio_output_update_time >= .1:
            print('on_output_gain_adjustment_value_changed =', widget.get_value())
            self.tnc.set_tx_volume(int(widget.get_value()))
            self.last_audio_output_update_time = now

    def on_output_gain_scale_button_release_event(self, widget, data = None):
        self.tnc.set_tx_volume(int(widget.get_value()))
        self.last_audio_output_update_time = time.time()

    def on_output_twist_adjustment_value_changed(self, widget):
        now = time.time()
        if now - self.last_audio_output_update_time >= .1:
            self.tnc.set_tx_twist(int(widget.get_value()))
            self.last_audio_output_update_time = now

    def on_output_twist_scale_button_release_event(self, widget, data = None):
        self.tnc.set_tx_twist(int(widget.get_value()))
        self.last_audio_output_update_time = time.time()

    def on_mark_tone_radio_button_toggled(self, widget):
        if widget.get_active():
            self.tnc.set_mark(True)
            self.tnc.set_space(False)

    def on_space_tone_radio_button_toggled(self, widget):
        if widget.get_active():
            self.tnc.set_mark(False)
            self.tnc.set_space(True)

    def on_both_tone_radio_button_toggled(self, widget):
        if widget.get_active():
            self.tnc.set_mark(True)
            self.tnc.set_space(True)

    def on_transmit_toggle_button_toggled(self, widget):
        
        if widget.get_active():
            self.tnc.set_mark(self.mark_tone_radio_button.get_active() or self.both_tone_radio_button.get_active())
            self.tnc.set_space(self.space_tone_radio_button.get_active() or self.both_tone_radio_button.get_active())
        self.tnc.set_ptt(widget.get_active())

    ### Power Settings...
    def init_power_settings_frame(self):
        self.power_settings_frame = self.builder.get_object("power_settings_frame")
        self.power_settings_frame.set_visible(False)
        self.battery_voltage_label = self.builder.get_object("battery_voltage_label")
        self.battery_level_bar = self.builder.get_object("battery_level_bar")
        self.battery_level_bar.add_offset_value("audio_input_level_bar-high", 10);
        self.battery_level_bar.add_offset_value("audio_input_level_bar-medium", 3);
        self.battery_level_bar.add_offset_value("audio_input_level_bar-low", 1);
        self.power_on_check_button = self.builder.get_object("power_on_check_button")
        self.power_off_check_button = self.builder.get_object("power_off_check_button")
    
    def on_power_settings_enter(self):
        print('on_power_settings_enter')
        if self.tnc is not None:
            self.tnc.get_battery_level()
        
    def on_power_settings_leave(self):
        print('on_power_settings_leave')
        
    def on_power_on_check_button_toggled(self, widget):
        self.tnc.set_usb_on(widget.get_active())

    def on_power_off_check_button_toggled(self, widget):
        self.tnc.set_usb_off(widget.get_active())
        

    ### KISS Parameters...
    def init_kiss_parameters_frame(self):
        self.kiss_parameters_frame = self.builder.get_object("kiss_parameters_frame")
        self.tx_delay_spin_button = self.builder.get_object("tx_delay_spin_button")
        self.slot_time_spin_button = self.builder.get_object("slot_time_spin_button")
        self.p_persist_spin_button = self.builder.get_object("p_persist_spin_button")
        self.full_duplex_check_button = self.builder.get_object("full_duplex_check_button")
        self.last_kiss_parameter_update_time = time.time()
    
    def on_kiss_parameters_enter(self):
        print('on_kiss_parameters_enter')
        
    def on_kiss_parameters_leave(self):
        print('on_kiss_parameters_leave')

    def on_tx_delay_adjustment_value_changed(self, widget):
        now = time.time()
        if now - self.last_kiss_parameter_update_time >= .1:
            self.tnc.set_tx_delay(int(widget.get_value()))
            self.last_kiss_parameter_update_time = now
   
    def on_tx_delay_spin_button_button_release_event(self, widget):
        self.tnc.set_tx_delay(int(widget.get_value()))
        self.last_kiss_parameter_update_time = time.time()

    def on_slot_time_adjustment_value_changed(self, widget):
        now = time.time()
        if now - self.last_kiss_parameter_update_time >= .1:
            self.tnc.set_time_slot(int(widget.get_value()))
            self.last_kiss_parameter_update_time = now

    def on_slot_time_spin_button_button_release_event(self, widget):
        self.tnc.set_time_slot(int(widget.get_value()))
        self.last_kiss_parameter_update_time = time.time()

    def on_p_persistence_adjustment_value_changed(self, widget):
        now = time.time()
        if now - self.last_kiss_parameter_update_time >= .1:
            self.tnc.set_persistence(int(widget.get_value()))
            self.last_kiss_parameter_update_time = now

    def on_p_persist_spin_button_button_release_event(self, widget):
        self.tnc.set_persistence(int(widget.get_value()))
        self.last_kiss_parameter_update_time = time.time()
        
    def on_full_duplex_check_button_toggled(self, widget):
        self.tnc.set_duplex(widget.get_active())


    ### Modem Settings...
    def init_modem_settings_frame(self):
        self.modem_settings_frame = self.builder.get_object("modem_settings_frame")
        self.modem_settings_frame.set_visible(False)
        self.dcd_check_button = self.builder.get_object("dcd_check_button")
        self.connection_tracking_check_button = self.builder.get_object("connection_tracking_check_button")
        self.verbose_output_check_button = self.builder.get_object("verbose_output_check_button")
    
    def on_modem_settings_enter(self):
        print('on_modem_settings_enter')
        
    def on_modem_settings_leave(self):
        print('on_modem_settings_leave')
        
    def on_dcd_check_button_toggled(self, widget):
        self.tnc.set_squelch_level((not widget.get_active()) * 2)
    
    def on_connection_tracking_check_button_toggled(self, widget):
        self.tnc.set_conn_track(widget.get_active())
    
    def on_verbose_output_check_button_toggled(self, widget):
        self.tnc.set_verbosity(widget.get_active())


    ### TNC Information...
    def init_tnc_information_frame(self):
        self.tnc_information_frame = self.builder.get_object("tnc_information_frame")
        self.hardware_version_label = self.builder.get_object("hardware_version_label")
        self.firmware_version_label = self.builder.get_object("firmware_version_label")
        self.mac_address_label = self.builder.get_object("mac_address_label")
        self.serial_number_label = self.builder.get_object("serial_number_label")
        self.date_time_label = self.builder.get_object("date_time_label")
    
    def on_tnc_information_enter(self):
        print('on_tnc_information_enter')
        
    def on_tnc_information_leave(self):
        print('on_tnc_information_leave')


    ### Update Firmware...
    def init_update_firmware_frame(self):
        self.update_firmware_frame = self.builder.get_object("update_firmware_frame")
        self.firmware_update_version_label = self.builder.get_object("firmware_update_version_label")
        self.firmware_file_chooser_button = self.builder.get_object("firmware_file_chooser_button")
        self.upload_button = self.builder.get_object("upload_button")
        self.firmware_progress_bar = self.builder.get_object("firmware_progress_bar")
        
        # File filter support in Glade is a bit janky.  It does not properly
        # associate the filter to the dialog unless it is done manually as
        # done below, and there is no way to name the filter in Glade.
        self.file_filter = self.builder.get_object("tnc1_2_file_filter")
        self.file_filter.set_name("TNC1 & TNC2 Firmware (*.hex)")
        self.firmware_file_chooser_button.add_filter(self.file_filter)
    
    def on_update_firmware_enter(self):
        print('on_update_firmware_enter')
        
    def on_update_firmware_leave(self):
        print('on_update_firmware_leave')

    def on_firmware_file_chooser_button_file_set(self, widget, data=None):
        self.firmware_file = self.firmware_file_chooser_button.get_filename()
        self.upload_button.set_sensitive(True)

    def on_upload_button_clicked(self, widget, data=None):
        confirm = Gtk.MessageDialog(self.main_window, 0,
            Gtk.MessageType.WARNING,
            Gtk.ButtonsType.OK_CANCEL,
            """You are about to upload a firmware image to the TNC.  This is irreversible and a potentially damaging operation.  Please ensure that the TNC is plugged into USB power and that a valid firmware image for the device has been selected.
            
Are you sure that you wish to proceed?""")
        confirm.set_title("Confirm Firmware Upload")
        response = confirm.run()
        confirm.destroy()
        if response == Gtk.ResponseType.CANCEL:
            return
        
        self.firmware_upload_complete = None
        # self.firmware_gui_tag = GObject.idle_add(self.check_firmware_upload_complete)
        self.sidebar.set_sensitive(False)
        print("firmware file =", self.firmware_file)
        self.tnc.upload_firmware(self.firmware_file, self)


    ### Save Settings...
    def init_save_settings_frame(self):
        self.save_settings_frame = self.builder.get_object("save_settings_frame")
        self.save_settings_frame.set_visible(False)
        self.save_settings_button = self.builder.get_object("save_settings_button")
    
    def on_save_settings_enter(self):
        print('on_save_settings_enter')
        
    def on_save_settings_leave(self):
        print('on_save_settings_leave')

    def on_save_settings_button_clicked(self, widget):
        self.tnc.save_eeprom_settings()

    ### TNC events
    
    def tnc_connect(self):
        self.stack.set_visible_child_name('audio_input')
        self.stack.set_sensitive(True)
        self.sidebar.set_sensitive(True)
        self.serial_port_combo_box_text.set_sensitive(False)
        self.connect_button.set_label("gtk-disconnect")
        self.firmware_progress_bar.set_text("Select firmware image...")

    def tnc_disconnect(self):
        self.stack.set_visible_child_name('audio_input')
        self.stack.set_sensitive(False)
        self.sidebar.set_sensitive(False)
        self.serial_port_combo_box_text.set_sensitive(True)
        self.connect_button.set_label("gtk-connect")
        self.connect_button.set_active(False)
        self.tnc = None

    ### Audio Input
    def tnc_rx_volume(self, value):
        self.audio_input_level_bar.set_value(value * 1.25)
    
    def tnc_input_atten(self, value):
        self.input_attenuation_box.set_visible(True)
        self.input_attenuation_check_button.set_active(value > 0);
    
    def tnc_input_gain(self, value):
        self.input_gain_box.set_visible(True)
        self.input_gain_scale.set_value(value);
    
    def tnc_input_twist(self, value):
        self.input_twist_box.set_visible(True)
        self.input_twist_scale.set_value(value);
    
    def tnc_min_input_twist(self, value):
        self.input_twist_min_label.set_text("{}dB".format(value))

    def tnc_max_input_twist(self, value):
        self.input_twist_max_label.set_text("{}dB".format(value))

    def tnc_min_input_gain(self, value):
        self.input_gain_min_label.set_text("{}".format(value))

    def tnc_max_input_gain(self, value):
        self.input_gain_max_label.set_text("{}".format(value))
    
    def tnc_adjust_input(self):
        self.input_auto_adjust_button.set_visible(True)
        self.input_auto_adjust_button.set_sensitive(True)

    ### Audio Output
    
    def tnc_ptt_style(self, value):
        
        self.ptt_style_box.set_visible(True)
        
        if value == 0:
            self.ptt_simplex_radio_button.set_active(True)
        else:
            self.ptt_multiplex_radio_button.set_active(True)

    def tnc_tx_volume(self, gain):
        
        self.output_gain_scale.set_value(gain)

    def tnc_tx_twist(self, gain):
        self.output_twist_box.set_visible(True)
        self.output_twist_scale.set_value(gain)


    ### Power Settings
    def tnc_battery_level(self, value):
        self.power_settings_frame.set_visible(True)
        self.battery_voltage_label.set_text(str(int(value)) + "mV")
        level_bar_value = min(max(0, value - 3300) / 90.0, 10.0)
        self.battery_level_bar.set_value(level_bar_value)

    def tnc_power_on(self, value):
        self.power_settings_frame.set_visible(True)
        self.power_on_check_button.set_sensitive(True)
        self.power_on_check_button.set_active(value)

    def tnc_power_off(self, value):
        self.power_settings_frame.set_visible(True)
        self.power_off_check_button.set_sensitive(True)
        self.power_off_check_button.set_active(value)
    
    ### KISS Parameters

    def tnc_tx_delay(self, value):
        self.tx_delay_spin_button.set_value(value)
    
    def tnc_slot_time(self, value):
        self.slot_time_spin_button.set_value(value)
    
    def tnc_persistence(self, value):
        self.p_persist_spin_button.set_value(value)
    
    def tnc_tx_tail(self, value):
        # No longer used or settable
        pass
    
    def tnc_duplex(self, value):
        self.full_duplex_check_button.set_sensitive(True)
        self.full_duplex_check_button.set_active(value)
 
    ### Modem Settings
    
    def tnc_dcd(self, value):
        self.modem_settings_frame.set_visible(True)
        self.dcd_check_button.set_sensitive(True)
        self.dcd_check_button.set_active(value == 0)

    def tnc_conn_track(self, value):
        self.modem_settings_frame.set_visible(True)
        self.connection_tracking_check_button.set_sensitive(True)
        self.connection_tracking_check_button.set_active(value)
    
    def tnc_verbose(self, value):
        self.modem_settings_frame.set_visible(True)
        self.verbose_output_check_button.set_sensitive(True)
        self.verbose_output_check_button.set_active(value)
    
    ### TNC Information
    
    def tnc_hardware_version(self, value):
        self.hardware_version_label.set_text(value)

    def tnc_firmware_version(self, value):
        self.firmware_version_label.set_text(value)
        self.firmware_update_version_label.set_text(value)

    def tnc_mac_address(self, value):
        self.mac_address_label.set_text(value)

    def tnc_serial_number(self, value):
        self.serial_number_label.set_text(value)

    def tnc_date_time(self, value):
        self.date_time_label.set_text(value)

    ### Update Firmware
    def tnc_dfu_firmware(self):
        self.update_firmware_frame.set_visible(False)
    
    ### Save Settings

    def tnc_eeprom_save(self):
        self.save_settings_frame.set_visible(True)
        self.save_settings_button.set_sensitive(True)

    def exception(self, ex):
        print(str(ex))
    
    ### Firmware Update Callbacks
    def is_firmware_update_complete(self):
        return self.firmware_upload_complete is not None
    
    def firmware_set_steps(self, steps):
        self.progress_bar_step = 1.0 / steps
        print("progress bar step: {}".format(self.progress_bar_step))
        GObject.idle_add(self.firmware_progress_bar.set_pulse_step, self.progress_bar_step)

    def firmware_writing(self):
        self.progress_bar_progress = 0.0
        GObject.idle_add(self.firmware_progress_bar.set_text, "Writing...")
        GObject.idle_add(self.firmware_progress_bar.set_fraction, self.progress_bar_progress)
    
    def firmware_verifying(self):
        self.progress_bar_progress = 0.0
        GObject.idle_add(self.firmware_progress_bar.set_text, "Verifying...")
        GObject.idle_add(self.firmware_progress_bar.set_fraction, self.progress_bar_progress)
    
    def firmware_pulse(self):
        self.progress_bar_progress += self.progress_bar_step
        # Pulse doesn't work for some unknown reason 
        # GObject.idle_add(self.firmware_progress_bar.pulse)
        GObject.idle_add(self.firmware_progress_bar.set_fraction, self.progress_bar_progress)
    
    def firmware_success(self):
        Notify.Notification.new("Firmware upload complete").show()
        self.firmware_upload_complete = True
        self.firmware_progress_bar.set_text("Firmware upload complete")
        self.sidebar.set_sensitive(True)
        self.tnc.disconnect()
    
    def firmware_failure(self, msg):
        Notify.Notification.new("Firmware upload failed: {}".format(msg)).show()
        self.firmware_upload_complete = False
        self.firmware_progress_bar.set_text("Firmware upload failed")
        self.sidebar.set_sensitive(True)

    def check_firmware_upload_complete(self):
        
        if not self.is_firmware_update_complete():
            self.firmware_gui_tag = GObject.idle_add(self.check_firmware_upload_complete)
            return
        
        self.tnc.upload_firmware_complete()


if __name__ == '__main__':

    GObject.threads_init()
    app = TncConfigApp()

