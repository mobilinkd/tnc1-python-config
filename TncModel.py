#!/bin/env python2.7

from __future__ import print_function, unicode_literals
from builtins import bytes, chr
import threading
import time
import datetime
import math
import traceback
from io import StringIO, BytesIO
from struct import pack, unpack
from gi.repository import GLib
from BootLoader import BootLoader
from bluetooth import *
import select
import binascii

class UTC(datetime.tzinfo):
    """UTC"""
    
    ZERO = datetime.timedelta(0)
    
    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO

utc = UTC()
    
def get_device_name(devices, address):
    
    x = [x[0] for x in devices if x[1] == address]
    if x:
        return x[0]
    else:
        return None
        
def available_devices():
    
    rfcomm_devices = find_service(uuid='00001101-0000-1000-8000-00805f9b34fb')
    return rfcomm_devices

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
        self.tmp = bytearray()
    
    def process(self, c):
        if self.escape:
            if c == self.TFEND:
                c = self.FEND
            elif c == self.TFESC:
                c = self.FESC
            else:
                # Bogus sequence
                self.escape = False
                return None
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
            # print self.tmp
            self.tmp = bytearray()
        else:
            self.tmp.append(c)
    
    def wait_packet_type(self, c, escape):
        
        if not escape and c == self.FEND: return # possible dupe
        self.packet.packet_type = c
        if c == 0x06:
            self.state = self.WAIT_SUB_TYPE
        else:
            self.packet.data = bytearray()
            self.state = self.WAIT_DATA
    
    def wait_sub_type(self, c, escape):
        self.packet.sub_type = c
        self.packet.data = bytearray()
        self.state = self.WAIT_DATA
    
    def wait_data(self, c, escape):
        if not escape and c == self.FEND:
            self.packet.ready = True
            self.state = self.WAIT_FEND
        else:
            self.packet.data.append(c)

class KissEncode(object):

    FEND = bytes(b'\xC0')
    FESC = bytes(b'\xDB')
    TFEND = bytes(b'\xDC')
    TFESC = bytes(b'\xDD')

    def __init__(self):
        pass
    
    def encode(self, data):
        
        buf = BytesIO()
        
        buf.write(self.FEND)
        
        for c in [x for x in data]:
            if c == self.FEND:
                buf.write(self.FESC)
                buf.write(self.TFEND)
            elif c == self.FESC:
                buf.write(c)
                buf.write(self.TFESC)
            else:
                buf.write(bytes([c]))

        buf.write(self.FEND)
        
        return buf.getvalue()
    

class TncModel(object):

    SET_TX_DELAY = bytes(b'\01%c')
    SET_PERSISTENCE = bytes(b'\02%c')
    SET_TIME_SLOT = bytes(b'\03%c')
    SET_TX_TAIL = bytes(b'\04%c')
    SET_DUPLEX = bytes(b'\05%c')
    
    GET_BATTERY_LEVEL = bytes(b'\06\06')
    
    SET_OUTPUT_VOLUME=bytes(b'\x06\x01%c')
    SET_OUTPUT_GAIN=bytes(b'\x06\x01%c%c')     # API 2.0, 16-bit signed
    SET_INPUT_TWIST=bytes(b'\x06\x18\%s')      # API 2.0, 0-100
    SET_OUTPUT_TWIST=bytes(b'\x06\x1a\%c')     # API 2.0, 0-100
    SET_INPUT_ATTEN=bytes(b'\06\02%c')
    SET_INPUT_GAIN=bytes(b'\06\02%c%c')        # API 2.0, 16-bit signed
    SET_SQUELCH_LEVEL=bytes(b'\06\03%c')
    
    GET_ALL_VALUES=bytes(b'\06\177')           # Get all settings and versions
    
    POLL_VOLUME=bytes(b'\06\04')               # One value
    STREAM_VOLUME=bytes(b'\06\05')             # Stream continuously
    ADJUST_INPUT_LEVELS=bytes(b'\06\x2b')      # API 2.0
    
    SET_DATETIME=bytes(b'\x06\x32%c%c%c%c%c%c%c')  # API 2.0, BCD YMDWHMS

    PTT_MARK=bytes(b'\06\07')
    PTT_SPACE=bytes(b'\06\010')
    PTT_BOTH=bytes(b'\06\011')
    PTT_OFF=bytes(b'\06\012')
    
    SET_BT_CONN_TRACK = bytes(b'\06\105%c')
    SAVE_EEPROM_SETTINGS = bytes(b'\06\052')
    
    SET_USB_POWER_ON = bytes(b'\06\111%c')
    SET_USB_POWER_OFF = bytes(b'\06\113%c')
    
    SET_VERBOSITY = bytes(b'\06\020%c');
    
    SET_PTT_CHANNEL = bytes(b'\06\117%c');
    GET_PTT_CHANNEL = bytes(b'\06\120');
    
    SET_PASSALL = bytes(b'\06\x51%c')
    SET_MODEM_TYPE = bytes(b'\06\xc1\x82%c')
    SET_RX_REVERSE_POLARITY = bytes(b'\06\x53%c')
    SET_TX_REVERSE_POLARITY = bytes(b'\06\x55%c')
    
    TONE_NONE = 0
    TONE_SPACE = 1
    TONE_MARK = 2
    TONE_BOTH = 3
    
    HANDLE_TX_DELAY = 33
    HANDLE_PERSISTENCE = 34
    HANDLE_SLOT_TIME = 35
    HANDLE_TX_TAIL = 36
    HANDLE_DUPLEX = 37
    
    HANDLE_INPUT_LEVEL = 4
    HANDLE_BATTERY_LEVEL = 6
    HANDLE_TX_VOLUME = 12
    HANDLE_TX_TWIST = 27            # API 2.0
    HANDLE_INPUT_ATTEN = 13         # API 1.0
    HANDLE_INPUT_GAIN = 13          # API 2.0
    HANDLE_INPUT_TWIST = 25         # API 2.0
    HANDLE_SQUELCH_LEVEL = 14
    HANDLE_VERBOSITY = 17
    
    HANDLE_FIRMWARE_VERSION = 40
    HANDLE_HARDWARE_VERSION = 41
    HANDLE_SERIAL_NUMBER = 47       # API 2.0
    HANDLE_MAC_ADDRESS = 48
    HANDLE_DATE_TIME = 49           # API 2.0
    HANDLE_BLUETOOTH_NAME = 66
    HANDLE_CONNECTION_TRACKING = 70
    HANDLE_USB_POWER_ON = 74
    HANDLE_USB_POWER_OFF = 76

    HANDLE_MIN_INPUT_TWIST = 121    # API 2.0
    HANDLE_MAX_INPUT_TWIST = 122    # API 2.0
    HANDLE_API_VERSION = 123        # API 2.0
    HANDLE_MIN_INPUT_GAIN = 124     # API 2.0
    HANDLE_MAX_INPUT_GAIN = 125     # API 2.0
    HANDLE_CAPABILITIES = 126
    HANDLE_EXTENDED_1 = 0xc1
    HANDLE_EXT1_SELECTED_MODEM_TYPE = 0x81
    HANDLE_EXT1_SUPPORTED_MODEM_TYPES = 0x83
    
    HANDLE_PTT_CHANNEL = 80
    HANDLE_PASSALL = 82
    HANDLE_RX_REVERSE_POLARITY = 84
    HANDLE_TX_REVERSE_POLARITY = 86
    
    CAP_EEPROM_SAVE = 0x0200
    CAP_ADJUST_INPUT = 0x0400
    CAP_DFU_FIRMWARE = 0x0800

    def __init__(self, app, device):
        self.app = app
        self.device = device
        self.decoder = KissDecode()
        self.encoder = KissEncode()
        self.ser = None
        self.thd = None
        self.tone = self.TONE_NONE
        self.ptt = False
        self.reading = False
        self.api_version = 0x0100
    
    def __del__(self):
        self.disconnect()

    def connected(self):
        return self.ser is not None
        
    def connect(self):
        if self.connected(): return
        
        try:
            # print("connecting to %s" % self.serial)
            self.ser = BluetoothSocket(RFCOMM)
            self.ser.connect((self.device['host'], self.device['port']))
            # print("connected")
            time.sleep(1)
            self.sio_reader = self.ser # io.BufferedReader(self.ser)
            self.sio_writer = self.ser # io.BufferedWriter(self.ser)
            self.app.tnc_connect()

            self.reading = True
            self.thd = threading.Thread(target=self.readSerial, args=(self.sio_reader,))
            self.thd.start()
            
            self.sio_writer.send(self.encoder.encode(self.PTT_OFF))
            
            time.sleep(1)
            self.sio_writer.send(self.encoder.encode(self.GET_ALL_VALUES))
            
            time.sleep(1)
            self.sio_writer.send(self.encoder.encode(self.STREAM_VOLUME))
            

        except Exception as e:
            self.app.exception(e)

    def internal_reconnect(self):
        try:
            self.reading = True
            self.thd = threading.Thread(target=self.readSerial, args=(self.sio_reader,))
            self.thd.start()
            return True
        except Exception as e:
            self.app.exception(e)
            return False
        
    def reconnect(self):
        if self.internal_reconnect():
            self.app.tnc_connect()
            self.sio_writer.send(self.encoder.encode(self.PTT_OFF))
            self.sio_writer.send(self.encoder.encode(self.GET_ALL_VALUES))
            self.sio_writer.send(self.encoder.encode(self.STREAM_VOLUME))
            

    def internal_disconnect(self):
        self.reading = False
        if self.thd is not None:
            try:
                if self.sio_writer is not None:
                    self.sio_writer.send(self.encoder.encode(self.POLL_VOLUME))
                
                self.thd.join()
                self.thd = None
            except Exception as e:
                self.app.exception(e)

    def disconnect(self):
        
        self.internal_disconnect()
        if self.app is not None: self.app.tnc_disconnect()
        if self.ser is not None: self.ser.close()
        self.ser = None
        self.sio_writer = None
        self.sio_reader = None
    
    def update_rx_volume(self, value):
        self.app.tnc_rx_volume(value)
    
    def handle_packet(self, packet):
        # print(packet.sub_type, packet.data)
        if packet.packet_type == 0x07:
            print(packet.data)
            self.app.notice(packet.data);
        elif packet.packet_type != 0x06:
            return
        elif packet.sub_type == self.HANDLE_INPUT_LEVEL:
            self.handle_input_level(packet)
        elif packet.sub_type == self.HANDLE_TX_VOLUME:
            self.handle_tx_volume(packet)
        elif packet.sub_type == self.HANDLE_TX_TWIST:
            self.handle_tx_twist(packet)
        elif packet.sub_type == self.HANDLE_BATTERY_LEVEL:
            self.handle_battery_level(packet)
        elif packet.sub_type == self.HANDLE_INPUT_ATTEN:
            self.handle_input_atten(packet)
        elif packet.sub_type == self.HANDLE_INPUT_TWIST:
            self.handle_input_twist(packet)
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
        elif packet.sub_type == self.HANDLE_SERIAL_NUMBER:
            self.handle_serial_number(packet)
        elif packet.sub_type == self.HANDLE_MAC_ADDRESS:
            self.handle_mac_address(packet)
        elif packet.sub_type == self.HANDLE_DATE_TIME:
            self.handle_date_time(packet)
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
        elif packet.sub_type == self.HANDLE_API_VERSION:
            self.handle_api_version(packet)
        elif packet.sub_type == self.HANDLE_MIN_INPUT_TWIST:
            self.handle_min_input_twist(packet)
        elif packet.sub_type == self.HANDLE_MAX_INPUT_TWIST:
            self.handle_max_input_twist(packet)
        elif packet.sub_type == self.HANDLE_MIN_INPUT_GAIN:
            self.handle_min_input_gain(packet)
        elif packet.sub_type == self.HANDLE_MAX_INPUT_GAIN:
            self.handle_max_input_gain(packet)
        elif packet.sub_type == self.HANDLE_PASSALL:
            self.handle_passall(packet)
        elif packet.sub_type == self.HANDLE_RX_REVERSE_POLARITY:
            self.handle_rx_reverse_polarity(packet)
        elif packet.sub_type == self.HANDLE_TX_REVERSE_POLARITY:
            self.handle_tx_reverse_polarity(packet)
        elif packet.sub_type == self.HANDLE_EXTENDED_1:
            self.handle_extended_range_1(packet)
        else:
            # print "handle_packet: unknown packet sub_type (%d)" % packet.sub_type
            # print "data:", packet.data
            pass
    
    def handle_extended_range_1(self, packet):
        extended_type = packet.data[0]
        packet.data = packet.data[1:]
        if extended_type == self.HANDLE_EXT1_SELECTED_MODEM_TYPE:
            self.handle_selected_modem_type(packet)
        elif extended_type == self.HANDLE_EXT1_SUPPORTED_MODEM_TYPES:
            self.handle_supported_modem_types(packet)
        else:
            pass # Unknown extended type
    
    def readSerial(self, sio):
        # print "reading..."
        while self.reading:
            try:
                block = bytes(sio.recv(160))
                if len(block) == 0: continue
                for c in block:
                    packet = self.decoder.process(c)
                    if packet is not None:
                        GLib.idle_add(self.handle_packet, packet)
                    # self.handle_packet(packet)
            except ValueError as e:
                self.app.exception(e)
                pass
        
        # print "done reading..."
    
    def handle_input_level(self, packet):
        v = packet.data[0]
        v = max(v, 1)
        volume = math.log(v) / math.log(2)
        # print(volume)
        self.app.tnc_rx_volume(volume)
    
    def handle_tx_volume(self, packet):
        if self.api_version == 0x0100:
            volume = packet.data[0]
        else:
            volume = (packet.data[0] * 256) + packet.data[1]
        self.app.tnc_tx_volume(volume)
    
    def handle_tx_twist(self, packet):
        twist = packet.data[0]
        self.app.tnc_tx_twist(twist)
    
    def handle_battery_level(self, packet):
        value = (packet.data[0] << 8) + packet.data[1]
        self.app.tnc_battery_level(value)
    
    # Also HANDLE_INPUT_GAIN
    def handle_input_atten(self, packet):
        if self.api_version == 0x0100:
            atten = packet.data[0]
            self.app.tnc_input_atten(atten != 0)
        else:
            gain = unpack('>h', packet.data)[0]
            self.app.tnc_input_gain(gain)
    
    def handle_input_twist(self, packet):
        twist = packet.data[0]
        self.app.tnc_input_twist(twist)
    
    def handle_squelch_level(self, packet):
        squelch = packet.data[0]
        self.app.tnc_dcd(squelch)
    
    def handle_tx_delay(self, packet):
        value = packet.data[0]
        self.app.tnc_tx_delay(value)
    
    def handle_persistence(self, packet):
        value = packet.data[0]
        self.app.tnc_persistence(value)
    
    def handle_slot_time(self, packet):
        value = packet.data[0]
        self.app.tnc_slot_time(value)
    
    def handle_tx_tail(self, packet):
        value = packet.data[0]
        self.app.tnc_tx_tail(value)
    
    def handle_duplex(self, packet):
        value = packet.data[0]
        self.app.tnc_duplex(value != 0)
    
    def handle_firmware_version(self, packet):
        self.app.tnc_firmware_version(packet.data.decode("utf-8"))
    
    def handle_hardware_version(self, packet):
        self.app.tnc_hardware_version(packet.data.decode("utf-8"))
    
    def handle_serial_number(self, packet):
        self.app.tnc_serial_number(packet.data.decode("utf-8"))
        return
    
    def handle_mac_address(self, packet):
        self.app.tnc_mac_address(':'.join('{:02X}'.format(a) for a in packet.data))
        return
   
    def handle_date_time(self, packet):
    
        def bcd_to_int(value):
            return ((value // 16) * 10) + (value & 0x0F)
            
        d = packet.data
        # print("raw date:", binascii.hexlify(d))
        year = bcd_to_int(d[0]) + 2000
        month = bcd_to_int(d[1])
        day = bcd_to_int(d[2])
        weekday = bcd_to_int(d[3])
        hour = bcd_to_int(d[4])
        minute = bcd_to_int(d[5])
        second = bcd_to_int(d[6])
        try:
            dt = datetime.datetime(year, month, day, hour, minute, second, tzinfo=utc)
            self.app.tnc_date_time(dt.isoformat())
        except Exception as ex:
            self.app.tnc_date_time("RTC ERROR")
            self.app.exception(ex)
    
    def handle_bluetooth_name(self, packet):
        pass
    
    def handle_bluetooth_connection_tracking(self, packet):
        self.app.tnc_conn_track(packet.data[0])
    
    def handle_verbosity(self, packet):
        self.app.tnc_verbose(packet.data[0])
        
    def handle_ptt_channel(self, packet):
        self.app.tnc_ptt_style(packet.data[0])
        
    def handle_usb_power_on(self, packet):
        self.app.tnc_power_on(packet.data[0])
        
    def handle_usb_power_off(self, packet):
        self.app.tnc_power_off(packet.data[0])
        
    def handle_capabilities(self, packet):
        if len(packet.data) < 2:
            return
        value = packet.data[1]
        if (value << 8) & self.CAP_EEPROM_SAVE:
            self.app.tnc_eeprom_save()
        if (value << 8) & self.CAP_ADJUST_INPUT:
            self.app.tnc_adjust_input()
        if (value << 8) & self.CAP_DFU_FIRMWARE:
            self.app.tnc_dfu_firmware()


    def handle_api_version(self, packet):
        if len(packet.data) < 2:
            return
        self.api_version = unpack('>h', packet.data)[0]

    def handle_min_input_twist(self, packet):
        self.app.tnc_min_input_twist(unpack('b', packet.data)[0])
   
    def handle_max_input_twist(self, packet):
        self.app.tnc_max_input_twist(unpack('b', packet.data)[0])
   
    def handle_min_input_gain(self, packet):
        self.app.tnc_min_input_gain(unpack('>h', packet.data)[0])
   
    def handle_max_input_gain(self, packet):
        self.app.tnc_max_input_gain(unpack('>h', packet.data)[0])

    def handle_passall(self, packet):
        self.app.tnc_passall(packet.data[0])

    def handle_rx_reverse_polarity(self, packet):
        self.app.tnc_rx_reverse_polarity(packet.data[0])

    def handle_tx_reverse_polarity(self, packet):
        self.app.tnc_tx_reverse_polarity(packet.data[0])

    def handle_selected_modem_type(self, packet):
        self.app.tnc_selected_modem_type(packet.data[0])

    def handle_supported_modem_types(self, packet):
        self.app.tnc_supported_modem_types(packet.data)

   
    def set_tx_volume(self, volume):
        try:
            if self.api_version == 0x0100:
                self.sio_writer.send(
                    self.encoder.encode(bytes(pack('>BBB', 6, 1, volume))))
            else:
                self.sio_writer.send(
                    self.encoder.encode(bytes(pack('>BBh', 6, 1, volume))))
            
        except Exception as e:
            print("volume={}".format(volume))
            raise
            self.app.exception(e)

    def set_tx_twist(self, twist):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(bytes(pack('>BBB', 6, 0x1a, twist))))
            
        except Exception as e:
            self.app.exception(e)

    def set_input_atten(self, value):
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_INPUT_ATTEN % (2 * value)))
            
        except Exception as e:
            self.app.exception(e)
    
    def set_squelch_level(self, value):
        """Used to set DCD"""
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_SQUELCH_LEVEL % (value)))
            
        except Exception as e:
            self.app.exception(e)
    
    def set_input_gain(self, gain):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(bytes(pack('>BBh', 6, 0x2, gain))))
            
        except Exception as e:
            self.app.exception(e)

    def set_input_twist(self, twist):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(bytes(pack('>BBb', 6, 0x18, twist))))
            
        except Exception as e:
            self.app.exception(e)
    
    def adjust_input(self):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.ADJUST_INPUT_LEVELS))
            
        except Exception as e:
            self.app.exception(e)

    def set_tx_delay(self, delay):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_TX_DELAY % delay))
            
        except Exception as e:
            self.app.exception(e)

    def set_persistence(self, p):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_PERSISTENCE % (p)))
            
        except Exception as e:
            self.app.exception(e)
    
    def set_time_slot(self, timeslot):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_TIME_SLOT % (timeslot)))
            
        except Exception as e:
            self.app.exception(e)
    
    def set_tx_tail(self, tail):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_TX_TAIL % (tail)))
            
        except Exception as e:
            self.app.exception(e)
    
    def set_duplex(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_DUPLEX % (value)))
            
        except Exception as e:
            self.app.exception(e)
    
    def set_conn_track(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_BT_CONN_TRACK % (value)))
            
        except Exception as e:
            self.app.exception(e)
    
    def set_verbosity(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_VERBOSITY % (value)))
            
        except Exception as e:
            self.app.exception(e)
    
    def set_passall(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_PASSALL % (value)))
        except Exception as e:
            self.app.exception(e)
    
    def set_rx_reverse_polarity(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_RX_REVERSE_POLARITY % (value)))
        except Exception as e:
            self.app.exception(e)
    
    def set_tx_reverse_polarity(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_TX_REVERSE_POLARITY % (value)))
        except Exception as e:
            self.app.exception(e)
    
    def set_modem_type(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_MODEM_TYPE % (value)))
        except Exception as e:
            self.app.exception(e)

    def set_usb_on(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_USB_POWER_ON % chr(value)))
            
        except Exception as e:
            self.app.exception(e)
        
    def set_usb_off(self, value):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_USB_POWER_OFF % (value)))
            
        except Exception as e:
            self.app.exception(e)
        
    
    def save_eeprom_settings(self):
        if self.sio_writer is None: return
        try:
            self.sio_writer.send(self.encoder.encode(self.SAVE_EEPROM_SETTINGS))
            
        except Exception as e:
            self.app.exception(e)

    def set_ptt_channel(self, value):
        if self.sio_writer is None: return
        
        try:
            self.sio_writer.send(self.encoder.encode(self.SET_PTT_CHANNEL % int(value)))
            self.sio_writer.send(self.encoder.encode(self.GET_PTT_CHANNEL))
            
        except Exception as e:
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
        
        if self.sio_writer is None: return

        self.ptt = value
        
        try:
            if value and self.tone != self.TONE_NONE:
                if self.tone == self.TONE_MARK:
                    self.sio_writer.send(self.encoder.encode(self.PTT_MARK))
                elif self.tone == self.TONE_SPACE:
                    self.sio_writer.send(self.encoder.encode(self.PTT_SPACE))
                elif self.tone == self.TONE_BOTH:
                    self.sio_writer.send(self.encoder.encode(self.PTT_BOTH))
            else:
                self.sio_writer.send(self.encoder.encode(self.PTT_OFF))
        
            
        except Exception as e:
            self.app.exception(e)
    
    def stream_audio_on(self):
        if self.sio_writer is None: return
        self.sio_writer.send(self.encoder.encode(self.STREAM_VOLUME))
    
    def stream_audio_off(self):
        if self.sio_writer is None: return
        self.sio_writer.send(self.encoder.encode(self.POLL_VOLUME))

    def get_battery_level(self):
        if self.sio_writer is None: return
        self.sio_writer.send(self.encoder.encode(self.GET_BATTERY_LEVEL))

    def upload_firmware_thd(self, filename, gui):

        try:
            bootloader = BootLoader(self.ser, self.ser, filename, gui)
        except Exception as e:
            traceback.print_exc()
            gui.firmware_failure(str(e))
            return

        try:
            bootloader.load()
            if not bootloader.verify():
                gui.firmware_failure("Firmware verification failed.")
                return
            bootloader.exit()
            time.sleep(5)
            gui.firmware_success()
        except Exception as e:
            traceback.print_exc()
            gui.firmware_failure(str(e))

        
    def upload_firmware(self, filename, gui):

        self.internal_disconnect()
        self.firmware_thd = threading.Thread(target=self.upload_firmware_thd, args=(filename, gui))
        self.firmware_thd.start()

    def upload_firmware_complete(self):
        
        self.firmware_thd.join()
        time.sleep(5)
        self.internal_reconnect()
        self.sio_writer.send(self.encoder.encode(self.GET_ALL_VALUES))


