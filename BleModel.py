#!/bin/env python2.7

import threading
import binascii
import time
import math
from StringIO import StringIO
import Queue
import struct

from BluetoothLE import TNCRequester, TNCResponse

class KissData(object):

    def __init__(self):
        self.packet_type = None;
        self.sub_type = None;
        self.data = None
        self.ready = False;
   
    def __repr__(self):
        s = StringIO()
        s.write('KissData[')
        s.write('type: %d, ' % self.packet_type)
        s.write('sub_type: %d, ' % self.sub_type)
        s.write('data: ')
        # s.write(['%02X' % ord(x) for x in self.data])
        s.write(repr(self.data))
        s.write(', ')
        s.write(self.ready)
        s.write(']')
        return s.getvalue()
    

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
        self.tmp = ""
    
    def process(self, c):
        # print '%02x' % c ,
        
        if self.escape:
            if c == self.TFEND:
                c = self.FEND
            elif c == self.TFESC:
                c = self.FESC
            else:
                # Bogus sequence
                self.escape = False
                if c == self.FESC:
                    self.state = self.WAIT_PACKET_TYPE
                else:
                    self.state = self.WAIT_FEND
                return None
        elif c == self.FESC:
            self.escape = True
            return None
            
        self.parser[self.state](c, self.escape)
        self.escape = False
        
        if self.packet is not None and self.packet.ready:
            tmp = self.packet
            self.packet = KissData()
            return tmp
        else:
            return None
    
    def wait_fend(self, c, escape):
    
        if c == self.FEND and not escape:
            self.state = self.WAIT_PACKET_TYPE
            self.packet = KissData()
            if self.tmp: print self.tmp
            self.tmp = ""
        else:
            self.tmp += chr(c)
    
    def wait_packet_type(self, c, escape):
        
        if not escape and c == self.FEND: return # possible dupe
        self.packet.packet_type = c
        self.state = self.WAIT_SUB_TYPE
    
    def wait_sub_type(self, c, escape):
        if not escape and c == self.FEND:
            self.state = self.WAIT_PACKET_TYPE
            return

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
        
        print "encoded %s" % str([c for c in data])
        
        return buf.getvalue()


class BleModel(object):

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
    SET_OUTPUT_TWIST="\06\032%c"
    GET_OUTPUT_TWIST="\06\033"
    SET_INPUT_VOLUME="\06\02%c" # UNUSED
    GET_INPUT_ATTEN="\06\015"   # UNUSED
    POLL_INPUT_TWIST="\06\054"
    SET_SQUELCH_LEVEL="\06\03%c"
    GET_ALL_VALUES="\06\177"    # Get all settings and versions
    
    POLL_VOLUME="\06\04"        # One value
    STREAM_VOLUME="\06\05"      # Stream continuously

    SEND_MARK="\06\07"
    SEND_SPACE="\06\010"
    SEND_BOTH="\06\011"
    STOP_TX="\06\012"
    
    GET_FIRMWARE_VERSION = "\06\050"
    SET_BT_CONN_TRACK = "\06\105%c"
    SAVE_EEPROM_SETTINGS = "\06\052"
    
    SET_USB_POWER_ON = "\06\111%c"
    SET_USB_POWER_OFF = "\06\113%c"
    
    SET_VERBOSITY = "\06\020%c";
    GET_VERBOSITY = "\06\021";
    
    SET_PTT_CHANNEL = "\06\117%c";
    GET_PTT_CHANNEL = "\06\120";
    
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
    HANDLE_VERBOSITY = 17
    
    HANDLE_OUTPUT_TWIST = 27
    
    HANDLE_FIRMWARE_VERSION = 40
    HANDLE_HARDWARE_VERSION = 41
    
    HANDLE_POLL_INPUT_TWIST = 44
    
    HANDLE_BLUETOOTH_NAME = 66
    HANDLE_CONNECTION_TRACKING = 70
    HANDLE_USB_POWER_ON = 74
    HANDLE_USB_POWER_OFF = 76
    HANDLE_CAPABILITIES = 126
    
    HANDLE_PTT_CHANNEL = 80
    
    CAP_EEPROM_SAVE = 0x0200
    
    LOG_2 = math.log(2)


    def __init__(self, app, mac):
        self.app = app
        self.mac = mac
        self.from_tnc = Queue.Queue()
        self.to_tnc = Queue.Queue()
        self.decoder = KissDecode()
        self.encoder = KissEncode()
        self.thd = None
        self.tone = self.TONE_NONE
        self.ptt = False
        self.reading = False
    
    def __del__(self):
        self.disconnect()

    def connected(self):
        return self.requester.is_connected()
    
    def connected_callback(self):
        # print "connected_callback"
        
        self.app.tnc_connect()

        self.reading = True
        self.thd = threading.Thread(target=self.read)
        self.thd.start()
        
        self.requester.write(self.encoder.encode(self.POLL_VOLUME))
        self.requester.write(self.encoder.encode(self.STOP_TX))
        self.requester.write(self.encoder.encode(self.GET_ALL_VALUES))

    
    def connect(self):
        try:
            self.requester = TNCRequester(self.mac,
                self.to_tnc, self.from_tnc, self.connected_callback)
            self.requester.connect()

        except Exception, e:
            self.app.tnc_exception(e)

    
    def disconnect(self):
        self.requester.disconnect()
        self.app.tnc_disconnect()
    
    def update_rx_volume(self, value):
        self.app.tnc_rx_volume(value)
    
    def handle_packet(self, packet):
        print packet
        level = ['DEBUG','INFO','WARN','ERROR','SEVERE']
        if packet.packet_type == 0x07:
            print "LOG(%s): %s" % (level[packet.sub_type], packet.data)
            return

        if packet.packet_type != 0x06:
            return
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
        elif packet.sub_type == self.HANDLE_VERBOSITY:
            self.handle_verbosity(packet)
        elif packet.sub_type == self.HANDLE_CAPABILITIES:
            self.handle_capabilities(packet)
        elif packet.sub_type == self.HANDLE_PTT_CHANNEL:
            self.handle_ptt_channel(packet)
        elif packet.sub_type == self.HANDLE_USB_POWER_ON:
            self.handle_usb_power_on(packet)
        elif packet.sub_type == self.HANDLE_USB_POWER_OFF:
            self.handle_usb_power_off(packet)
        elif packet.sub_type == self.HANDLE_OUTPUT_TWIST:
            self.handle_output_twist(packet)
        elif packet.sub_type == self.HANDLE_POLL_INPUT_TWIST:
            self.handle_poll_input_twist(packet)
        else:
            # print "handle_packet: unknown packet sub_type (%d)" % packet.sub_type
            # print "data:", packet.data
            pass
    
    def read(self):
        # print "reading..."
        while True:
            try:
                data = self.from_tnc.get()
                if data is None: break
                for c in data:
                    packet = self.decoder.process(ord(c[0]))
                    if packet is not None:
                        self.handle_packet(packet)
            except Exception, e:
                self.app.tnc_exception(e)
                pass
        
        # print "done reading..."
    
    def handle_rx_volume(self, packet):
        if len(packet.data) == 1:
            v = ord(packet.data[0])
        else:
            v = ord(packet.data[0])
        v = max(v, 1)
        volume = math.log(v) / BleModel.LOG_2
        self.app.tnc_rx_volume(volume)
    
    def handle_tx_volume(self, packet):
        volume = ord(packet.data[0])
        self.app.tnc_tx_volume(volume)
    
    def handle_output_twist(self, packet):
        twist = ord(packet.data[0])
        self.app.tnc_tx_twist(twist)
    
    def handle_battery_level(self, packet):
        value = (ord(packet.data[0]) << 8) + ord(packet.data[1])
        self.app.tnc_battery_level(value)
    
    def handle_input_atten(self, packet):
        pass
    
    def handle_poll_input_twist(self, packet):
        g1200i, g2200i = struct.unpack('!hh', packet.data)
        g1200 = g1200i / 256.0
        g2200 = g2200i / 256.0
        self.app.tnc_receive_twist_levels(g1200, g2200)
        print "twist:", g1200, g2200
        pass
    
    def handle_squelch_level(self, packet):
        pass
    
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
        self.app.tnc_hardware_version(packet.data)
    
    def handle_bluetooth_name(self, packet):
        pass
    
    def handle_bluetooth_connection_tracking(self, packet):
        pass
    
    def handle_verbosity(self, packet):
        pass
        
    def handle_ptt_channel(self, packet):
        self.app.tnc_ptt_style(ord(packet.data[0]))
        
    def handle_usb_power_on(self, packet):
        self.app.tnc_power_on(ord(packet.data[0]))
        
    def handle_usb_power_off(self, packet):
        self.app.tnc_power_off(ord(packet.data[0]))
        
    def handle_capabilities(self, packet):
        # print ord(packet.data[0])
        if len(packet.data) < 2:
            return
        value = ord(packet.data[1])
        if (value << 8) & self.CAP_EEPROM_SAVE:
            self.app.tnc_eeprom_save()
    
    def set_tx_volume(self, volume):
        try:
            self.requester.write(self.encoder.encode(self.SET_OUTPUT_VOLUME % chr(volume)))
        except Exception, e:
            self.app.tnc_exception(e)

    def set_tx_twist(self, twist):
        try:
            self.requester.write(self.encoder.encode(self.SET_OUTPUT_TWIST % chr(twist)))
        except Exception, e:
            self.app.tnc_exception(e)

    def set_tx_delay(self, delay):
        try:
            self.requester.write(self.encoder.encode(self.SET_TX_DELAY % chr(delay)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
    def set_input_atten(self, value):
        try:
            self.requester.write(self.encoder.encode(self.SET_INPUT_VOLUME % chr(2 * value)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
    def set_squelch_level(self, value):
        try:
            self.requester.write(self.encoder.encode(self.SET_SQUELCH_LEVEL % chr(value)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    

    def set_persistence(self, p):
        try:
            self.requester.write(self.encoder.encode(self.SET_PERSISTENCE % chr(p)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
    def set_time_slot(self, timeslot):
        try:
            self.requester.write(self.encoder.encode(self.SET_TIME_SLOT % chr(timeslot)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
    def set_tx_tail(self, tail):
        try:
            self.requester.write(self.encoder.encode(self.SET_TX_TAIL % chr(tail)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
    def set_duplex(self, value):
        try:
            self.requester.write(self.encoder.encode(self.SET_DUPLEX % chr(value)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
    def set_conn_track(self, value):
        try:
            self.requester.write(self.encoder.encode(self.SET_BT_CONN_TRACK % chr(value)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
    def set_verbosity(self, value):
        try:
            self.requester.write(self.encoder.encode(self.SET_VERBOSITY % chr(value)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
    def set_usb_on(self, value):
        try:
            self.requester.write(self.encoder.encode(self.SET_USB_POWER_ON % chr(value)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
        
    def set_usb_off(self, value):
        try:
            self.requester.write(self.encoder.encode(self.SET_USB_POWER_OFF % chr(value)))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
        
    
    def save_eeprom_settings(self):
        try:
            self.requester.write(self.encoder.encode(self.SAVE_EEPROM_SETTINGS))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)

    def set_ptt_channel(self, value):
        
        try:
            self.requester.write(self.encoder.encode(self.SET_PTT_CHANNEL % chr(int(value))))
            self.requester.write(self.encoder.encode(self.GET_PTT_CHANNEL))
            self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        except Exception, e:
            self.app.tnc_exception(e)
    
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
                    self.requester.write(self.encoder.encode(self.SEND_MARK))
                elif self.tone == self.TONE_SPACE:
                    self.requester.write(self.encoder.encode(self.SEND_SPACE))
                elif self.tone == self.TONE_BOTH:
                    self.requester.write(self.encoder.encode(self.SEND_BOTH))
            else:
                self.requester.write(self.encoder.encode(self.STOP_TX))
                self.requester.write(self.encoder.encode(self.STREAM_VOLUME))
        
        except Exception, e:
            self.app.tnc_exception(e)
