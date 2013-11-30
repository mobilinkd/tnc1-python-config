#!/bin/env python2.7

import threading
import serial
import time
import math
from StringIO import StringIO

from BootLoader import BootLoader

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
            if c == self.TFEND:
                c = self.FEND
            elif c == self.TFESC:
                c = self.FESC
            else:
                raise ValueError("Invalid KISS escape sequence received")
        elif c == self.FESC:
            self.escape = True
            return None
            
        self.parser[self.state](c, self.escape)
        self.escape = False
        
        if self.packet is not None and self.packet.ready:
            return self.packet
        else:
            return None
    
    def wait_fend(self, c, escape):
    
        if c == self.FEND:
            self.state = self.WAIT_PACKET_TYPE
            self.packet = KissData()
    
    def wait_packet_type(self, c, escape):
        
        if not escape and c == self.FEND: return # possible dupe
        if c != 0x06:
            raise ValueError("Invalid KISS packet type received (%d)" % c)
        self.packet.packet_type = c
        self.state = self.WAIT_SUB_TYPE
    
    def wait_sub_type(self, c, escape):
        self.packet.sub_type = c
        self.packet.data = ""
        self.state = self.WAIT_DATA
    
    def wait_data(self, c, escape):
        if not escape and c == self.FEND:
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
    GET_ALL_VALUES="\06\177"   # Get all settings and versions
    
    POLL_VOLUME="\06\04"        # One value
    STREAM_VOLUME="\06\05"      # Stream continuously

    SEND_MARK="\06\07"
    SEND_SPACE="\06\010"
    SEND_BOTH="\06\011"
    STOP_TX="\06\012"
    
    GET_FIRMWARE_VERSION = "\06\050"
    SET_BT_CONN_TRACK = "\06\105%c"
    
    TONE_NONE = 0
    TONE_SPACE = 1
    TONE_MARK = 2
    TONE_BOTH = 3
    
    HANDLE_TX_DELAY = 33
    HANDLE_PERSISTENCE = 34
    HANDLE_SLOT_TIME = 35
    HANDLE_TX_TAIL = 36
    HANDLE_DUPLEX = 37
    
    HANDLE_RX_VOLUME = 4
    HANDLE_BATTERY_LEVEL = 6
    HANDLE_TX_VOLUME = 12
    HANDLE_INPUT_ATTEN = 13
    HANDLE_SQUELCH_LEVEL = 14
    
    HANDLE_FIRMWARE_VERSION = 40
    HANDLE_HARDWARE_VERSION = 41
    HANDLE_BLUETOOTH_NAME = 66
    HANDLE_CONNECTION_TRACKING = 70
    

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
            
            self.sio_writer.write(self.encoder.encode(self.STOP_TX))
            self.sio_writer.write(self.encoder.encode(self.GET_ALL_VALUES))
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

            self.sio_writer.write(self.encoder.encode(self.STOP_TX))
            self.sio_writer.write(self.encoder.encode(self.GET_ALL_VALUES))
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
        if packet.sub_type == self.HANDLE_RX_VOLUME:
            self.handle_rx_volume(packet)
        elif packet.sub_type == self.HANDLE_TX_VOLUME:
            self.handle_tx_volume(packet)
        elif packet.sub_type == self.HANDLE_BATTERY_LEVEL:
            self.handle_battery_level(packet)
        elif packet.sub_type == self.HANDLE_INPUT_ATTEN:
            self.handle_input_atten(packet)
        elif packet.sub_type == self.HANDLE_SQUELCH_LEVEL:
            self.handle_squelch_level(packet)
        elif packet.sub_type == self.HANDLE_TX_DELAY:
            self.handle_tx_delay(packet)
        elif packet.sub_type == self.HANDLE_PERSISTENCE:
            self.handle_persistence(packet)
        elif packet.sub_type == self.HANDLE_SLOT_TIME:
            self.handle_slot_time(packet)
        elif packet.sub_type == self.HANDLE_TX_TAIL:
            self.handle_tx_tail(packet)
        elif packet.sub_type == self.HANDLE_DUPLEX:
            self.handle_duplex(packet)
        elif packet.sub_type == self.HANDLE_FIRMWARE_VERSION:
            self.handle_firmware_version(packet)
        elif packet.sub_type == self.HANDLE_HARDWARE_VERSION:
            self.handle_hardware_version(packet)
        elif packet.sub_type == self.HANDLE_BLUETOOTH_NAME:
            self.handle_bluetooth_name(packet)
        elif packet.sub_type == self.HANDLE_CONNECTION_TRACKING:
            self.handle_bluetooth_connection_tracking(packet)
        else:
            print "handle_packet: unknown packet sub_type (%d)" % packet.sub_type
            print "data:", packet.data
    
    def readSerial(self, sio):
        # print "reading..."
        while self.reading:
            try:
                c = sio.read(1)
                if len(c) == 0: continue
                packet = self.decoder.process(ord(c[0]))
                if packet is not None:
                    self.handle_packet(packet)
            except ValueError, e:
                self.app.exception(e)
                pass
        
        # print "done reading..."
    
    def handle_rx_volume(self, packet):
        v = ord(packet.data[0])
        v = max(v, 1)
        volume = math.log(v) / math.log(2)
        self.app.tnc_rx_volume(volume)
    
    def handle_tx_volume(self, packet):
        volume = ord(packet.data[0])
        self.app.tnc_tx_volume(volume)
    
    def handle_battery_level(self, packet):
        value = (ord(packet.data[0]) << 8) + ord(packet.data[1])
        # print "Battery level:", value
        self.app.tnc_battery_level(value)
    
    def handle_input_atten(self, packet):
        atten = ord(packet.data[0])
        self.app.tnc_input_atten(atten != 0)
    
    def handle_squelch_level(self, packet):
        squelch = ord(packet.data[0])
        self.app.tnc_dcd(squelch)
    
    def handle_tx_delay(self, packet):
        value = ord(packet.data[0])
        self.app.tnc_tx_delay(value)
    
    def handle_persistence(self, packet):
        value = ord(packet.data[0])
        self.app.tnc_persistence(value)
    
    def handle_slot_time(self, packet):
        value = ord(packet.data[0])
        self.app.tnc_slot_time(value)
    
    def handle_tx_tail(self, packet):
        value = ord(packet.data[0])
        self.app.tnc_tx_tail(value)
    
    def handle_duplex(self, packet):
        value = ord(packet.data[0])
        self.app.tnc_duplex(value != 0)
    
    def handle_firmware_version(self, packet):
        self.app.tnc_firmware_version(packet.data)
    
    def handle_hardware_version(self, packet):
        pass
    
    def handle_bluetooth_name(self, packet):
        pass
    
    def handle_bluetooth_connection_tracking(self, packet):
        self.app.tnc_conn_track(ord(packet.data[0]))
    
    def set_tx_volume(self, volume):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_OUTPUT_VOLUME % chr(volume)))
            self.sio_writer.write(self.encoder.encode(self.GET_ALL_VALUES))
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
    
    def set_input_atten(self, value):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_INPUT_VOLUME % chr(2 * value)))
            self.sio_writer.write(self.encoder.encode(self.STREAM_VOLUME))
            self.sio_writer.flush()
        except Exception, e:
            self.app.exception(e)
    
    def set_squelch_level(self, value):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_SQUELCH_LEVEL % chr(value)))
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
    
    def set_conn_track(self, value):
        try:
            self.sio_writer.write(self.encoder.encode(self.SET_BT_CONN_TRACK % chr(value)))
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
        # print "PTT: %s, Tone=%d" % (str(value), self.tone)
        
        self.ptt = value
        
        try:
            if value and self.tone != self.TONE_NONE:
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
    
    def upload_firmware_thd(self, filename, gui):

        try:
            bootloader = BootLoader(self.ser, self.ser, filename, gui)
        except Exception, e:
            self.ser.close()
            self.ser = None
            self.sio_reader = None
            self.sio_writer = None
            gui.failure(str(e))
            return

        try:
            bootloader.load()
            if not bootloader.verify():
                bootloader.chip_erase()
                gui.failure("Firmware verification failed.")
                return
            bootloader.exit()
            self.ser.close()
            self.ser = None
            self.sio_reader = None
            self.sio_writer = None
            time.sleep(5)
            gui.success()
        except Exception, e:
            bootloader.chip_erase()
            gui.failure(str(e))

        
    def upload_firmware(self, filename, gui):

        self.disconnect()
        self.firmware_thd = threading.Thread(target=self.upload_firmware_thd, args=(filename, gui))
        self.firmware_thd.start()    

    def upload_firmware_complete(self):
        
        self.firmware_thd.join()
        self.connect()
