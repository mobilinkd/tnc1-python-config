#!/usr/bin/env python2.7

import sys
import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GdkPixbuf,GObject,Pango,Gdk

import serial
import serial.tools
import serial.tools.list_ports
import io
import glob
import threading
import math
import time
from StringIO import StringIO
from Avr109 import Avr109

def comports():
    if os.name == 'posix':
        devices = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/rfcomm*')
        return [(d, serial.tools.list_ports.describe(d), serial.tools.list_ports.hwinfo(d)) for d in devices]
    else:
        print [x for x in serial.tools.list_ports.comports()]
        return serial.tools.list_ports.comports()


class KissData(object):

    def __init__(self):
        self.packet_type = None;
        self.sub_type = None;
        self.data = None
        self.ready = False;
    

class KissDecode(object):

    WAIT_FEND = 1
    WAIT_PACKET_TYPE = 2
    WAIT_SUB_TYPE = 3
    WAIT_DATA = 4

    FEND = 0xC0
    FESC = 0xDB
    TFEND = 0xDC
    TFESC = 0xDD

    def __init__(self):
        self.state = self.WAIT_FEND
        self.packet = KissData()
        self.escape = False
        self.parser = {
            self.WAIT_FEND: self.wait_fend,
            self.WAIT_PACKET_TYPE: self.wait_packet_type,
            self.WAIT_SUB_TYPE: self.wait_sub_type,
            self.WAIT_DATA: self.wait_data}
    
    def process(self, c):
        if self.escape:
            self.escape = False
            if c == self.TFEND:
                c = self.FEND
            elif c == self.TFESC:
                c = self.FESC
            else:
                raise ValueError("Invalid KISS escape sequence received")
        elif c == self.FESC:
            self.escape = True
            return None
            
        self.parser[self.state](c)
        
        if self.packet is not None and self.packet.ready:
            return self.packet
        else:
            return None
    
    def wait_fend(self, c):
    
        if c == self.FEND:
            self.state = self.WAIT_PACKET_TYPE
            self.packet = KissData()
    
    def wait_packet_type(self, c):
        
        if c == self.FEND: return # possible dupe
        if c != 0x06:
            raise ValueError("Invalid KISS packet type received (%d)" % c)
        self.packet.packet_type = c
        self.state = self.WAIT_SUB_TYPE
    
    def wait_sub_type(self, c):
        self.packet.sub_type = c
        self.packet.data = ""
        self.state = self.WAIT_DATA
    
    def wait_data(self, c):
        if c == self.FEND:
            self.packet.ready = True
            self.state = self.WAIT_FEND
        else:
            self.packet.data += chr(c)

class KissEncode(object):

    FEND = 0xC0
    FESC = 0xDB
    TFEND = 0xDC
    TFESC = 0xDD

    def __init__(self):
        pass
    
    def encode(self, data):
        
        buf = StringIO()
        
        buf.write(chr(self.FEND))
        
        for c in [ord(x) for x in data]:
            if c == self.FEND:
                buf.write(chr(self.FESC))
                buf.write(chr(self.TFEND))
            elif c == self.FESC:
                buf.write(chr(c))
                buf.write(chr(self.TFESC))
            else:
                buf.write(chr(c))

        buf.write(chr(self.FEND))
        
        return buf.getvalue()
    

class TncModel(object):

    SET_TX_DELAY = "\01%c"
    GET_TX_DELAY = "\06\041"
    SET_PERSISTENCE = "\02%c"
    GET_PERSISTENCE = "\06\042"
    SET_TIME_SLOT = "\03%c"
    GET_TIME_SLOT = "\06\043"
    SET_TX_TAIL = "\04%c"
    GET_TX_TAIL = "\06\044"
    SET_DUPLEX = "\05%c"
    GET_DUPLEX = "\06\045"
    
    SET_OUTPUT_VOLUME="\06\01%c"
    GET_OUTPUT_VOUME="\06\014"
    SET_INPUT_VOLUME="\06\02%c" # UNUSED
    GET_INPUT_VOUME="\06\015"   # UNUSED
    SET_SQUELCH_LEVEL="\06\03%c"
    
    POLL_VOLUME="\06\04"        # One value
    STREAM_VOLUME="\06\05"      # Stream continuously

    SEND_MARK="\06\07"
    SEND_SPACE="\06\010"
    SEND_BOTH="\06\011"
    STOP_TX="\06\012"
    
    GET_FIRMWARE_VERSION = "\06\050"
    
    TONE_NONE = 0
    TONE_SPACE = 1
    TONE_MARK = 2
    TONE_BOTH = 3

    def __init__(self, app, ser):
        self.app = app
        self.serial = ser
        self.decoder = KissDecode()
        self.encoder = KissEncode()
        self.ser = None
        self.thd = None
        self.tone = self.TONE_NONE
        self.ptt = False
        self.reading = False
    
    def __del__(self):
        self.disconnect()


    def connected(self):
        return self.ser is not None
        
    def connect(self):
        if self.connected(): return
        
        try:
            print "connecting to %s" % self.serial
            self.ser = serial.Serial(self.serial, 115200, timeout=.1)
            self.sio_reader = self.ser # io.BufferedReader(self.ser)
            self.sio_writer = self.ser # io.BufferedWriter(self.ser)
            self.app.tnc_connect()

            self.reading = True
            self.thd = threading.Thread(target=self.readSerial, args=(self.sio_reader,))
            self.thd.start()

            self.sio_writer.write(self.encoder.encode(self.GET_OUTPUT_VOUME))
            self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
            self.sio_writer.flush()

        except Exception, e:
            self.app.exception(e)

    def reconnect(self):
        try:
            self.sio_reader = self.ser
            self.sio_writer = self.ser
            self.app.tnc_connect()

            self.reading = True
            self.thd = threading.Thread(target=self.readSerial, args=(self.sio_reader,))
            self.thd.start()

            self.sio_writer.write(self.encoder.encode(self.GET_OUTPUT_VOUME))
            self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)
        
    
    def disconnect(self):
        self.reading = False
        if self.thd is not None:
            try:
                self.sio_writer.write(self.encoder.encode(self.POLL_VOLUME))
                self.sio_writer.flush()
                self.thd.join()
                self.thd = None
            except Exception, e:
                self.app.exception(e)

        self.app.tnc_disconnect()
    
    def update_rx_volume(self, value):
        self.app.tnc_rx_volume(value)
    
    def handle_packet(self, packet):
        if packet.sub_type == 4:
            v = ord(packet.data[0])
            v = max(v, 1)
            volume = math.log(v) / math.log(2)
            self.app.tnc_rx_volume(volume)
        elif packet.sub_type == 12:
            volume = ord(packet.data[0])
            self.app.tnc_tx_volume(volume)
        else:
            print "handle_packet: unknown packet sub_type (%d)" % packet.sub_type
    
    def readSerial(self, sio):
        print "reading..."
        while self.reading:
            try:
                c = sio.read(1)
                if len(c) == 0: continue
                packet = self.decoder.process(ord(c[0]))
                if packet is not None:
                    self.handle_packet(packet)
            except ValueError, e:
                self.app.exception(e)
        
        print "done reading..."
    
    def set_tx_volume(self, volume):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_OUTPUT_VOLUME % chr(volume)))
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)

    def set_tx_delay(self, delay):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_TX_DELAY % chr(delay)))
            self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)
    
    def set_persistence(self, p):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_PERSISTENCE % chr(p)))
            self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)
    
    def set_time_slot(self, timeslot):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_TIME_SLOT % chr(timeslot)))
            self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)
    
    def set_tx_tail(self, tail):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_TX_TAIL % chr(tail)))
            self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)
    
    def set_duplex(self, value):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_DUPLEX % chr(value)))
            self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)
    
    def set_mark(self, value):
        if value:
            self.tone |= self.TONE_MARK
        else:
            self.tone &= self.TONE_SPACE
        self.set_ptt(self.ptt)
    
    def set_space(self, value):
        if value:
            self.tone |= self.TONE_SPACE
        else:
            self.tone &= self.TONE_MARK
        self.set_ptt(self.ptt)
    
    def set_ptt(self, value):
        print "PTT: %s, Tone=%d" % (str(value), self.tone)
        
        self.ptt = value
        
        try:
            if value & self.tone != self.TONE_NONE:
                if self.tone == self.TONE_MARK:
                    self.sio_writer.write(self.encoder.encode(self.SEND_MARK))
                elif self.tone == self.TONE_SPACE:
                    self.sio_writer.write(self.encoder.encode(self.SEND_SPACE))
                elif self.tone == self.TONE_BOTH:
                    self.sio_writer.write(self.encoder.encode(self.SEND_BOTH))
            else:
                self.sio_writer.write(self.encoder.encode(self.STOP_TX))
                self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
        
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)
    
    def upload_firmware(self, filename):
        self.disconnect()
        
        self.sio_reader = self.ser

        try:
            bootloader = Avr109(self.sio_reader, self.sio_writer, filename)
            bootloader.start()
            bootloader.initialize()
            bootloader.enter_program_mode()
            bootloader.leave_program_mode()
            bootloader.exit_bootloader()    # Reboot
        except Exception, e:
            self.app.exception(e)
        
        self.sio_reader = None
        self.sio_writer = None
        
        self.reconnect()
    
class MobilinkdTnc1Config(object):

    def __init__(self):
        self.tnc = None
        self.connect_message = None
        GObject.threads_init()
        self.builder = Gtk.Builder()
        self.builder.add_from_file("glade/MobilinkdTnc1Config.glade")
        
        self.window = self.builder.get_object("window")
        self.window.connect("delete-event", self.close)
        
        self.init_serial_port_combobox()
        self.init_transmit_volume()
        self.init_receive_volume()
        self.init_kiss_parameters()
        self.init_firmware_section()
        self.tnc_disconnect()
        
        self.status = self.builder.get_object("statusbar")
        self.builder.connect_signals(self)

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
    
    def on_transmit_volume_scale_value_changed(self, widget, data=None):
        self.tnc.set_tx_volume(int(widget.get_value()))

    def init_receive_volume(self):
        self.receive_volume_levelbar = self.builder.get_object("receive_volume_levelbar")
        self.receive_volume_levelbar.add_offset_value(Gtk.LEVEL_BAR_OFFSET_LOW, 5.0)
        self.receive_volume_levelbar.add_offset_value(Gtk.LEVEL_BAR_OFFSET_HIGH, 7.0)
        self.receive_volume_levelbar.set_value(0.0)

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
    
    def on_dcd_toggled(self, widget, data=None):
        pass
    
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
    
    def on_firmware_file_chooser_button_file_set(self, widget, data=None):
        self.firmware_file = self.firmware_file_chooser_button.get_filename()
        self.upload_button.set_sensitive(True)
        
    def on_upload_button_clicked(self, widget, data=None):
        self.tnc.upload_firmware(self.firmware_file)
    
    def tnc_connect(self):
        self.transmit_volume_scale.set_sensitive(True)
        self.mark_toggle_button.set_sensitive(True)
        self.mark_toggle_button.set_active(False)
        self.space_toggle_button.set_sensitive(True)
        self.space_toggle_button.set_active(False)
        self.ptt_toggle_button.set_sensitive(True)
        self.ptt_toggle_button.set_active(False)
        
        self.dcd_toggle_button.set_sensitive(True)
        self.dcd_toggle_button.set_active(False)
        
        self.kiss_tx_delay_spin_button.set_sensitive(True)
        
        self.kiss_persistence_spin_button.set_sensitive(True)
        self.kiss_slot_time_spin_button.set_sensitive(True)
        self.kiss_tx_tail_spin_button.set_sensitive(True)
        
        self.kiss_duplex_toggle_button.set_sensitive(True)
        self.kiss_duplex_toggle_button.set_active(False)
        
        self.firmware_file_chooser_button.set_sensitive(True)
        self.upload_button.set_sensitive(False)
        
        
    def tnc_disconnect(self):
        self.transmit_volume_scale.set_sensitive(False)
        self.mark_toggle_button.set_sensitive(False)
        self.space_toggle_button.set_sensitive(False)
        self.ptt_toggle_button.set_sensitive(False)
        self.dcd_toggle_button.set_sensitive(False)
        self.kiss_tx_delay_spin_button.set_sensitive(False)
        self.kiss_persistence_spin_button.set_sensitive(False)
        self.kiss_slot_time_spin_button.set_sensitive(False)
        self.kiss_tx_tail_spin_button.set_sensitive(False)
        self.kiss_duplex_toggle_button.set_sensitive(False)
            
        self.firmware_file_chooser_button.set_sensitive(False)
        self.upload_button.set_sensitive(False)

    def tnc_rx_volume(self, value):
        self.receive_volume_levelbar.set_value(value)
        self.receive_volume_progressbar.set_fraction(value / 8.0)
        
    def tnc_tx_volume(self, value):
        self.transmit_volume_scale.set_value(value)
        
    def exception(self, e):
        self.status.push(1, str(e))
        

if __name__ == '__main__':

    GObject.threads_init()
    app = MobilinkdTnc1Config()

