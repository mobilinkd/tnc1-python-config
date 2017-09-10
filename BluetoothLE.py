'''
Created on Aug 30, 2017

@author: rob
'''

from bluetooth.ble import DiscoveryService
from bluetooth.ble import GATTRequester, GATTResponse

import binascii
import Queue
import threading

from time import sleep
from cStringIO import StringIO

UART_CHARACTERISTIC = '0000ffe1-0000-1000-8000-00805f9b34fb'


class TNCResponse(GATTResponse):
    def __init__(self, callback):
        self.callback = callback
        GATTResponse.__init__(self)
        
    def on_response(self, data):
        print("NotifyTNC data: {}".format(binascii.hexlify(data)))
        if len(data) != 1: self.callback()

class TNCRequester(GATTRequester):
    """
    The requester connected to the specific GATT characteristic.
    """

    def __init__(self, mac, handle, to_tnc, from_tnc, callback):
        self.thread = None
        self.mac = mac
        self.handle = handle
        self.input_queue = from_tnc
        self.output_queue = to_tnc
        self.response = TNCResponse(callback)
        GATTRequester.__init__(self, mac, False)

    def connect(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def get_handle(self): return self.handle
    
    def write(self, data):
        self.output_queue.put(data)

    def on_notification(self, handle, data):
        # print "notified!"
        self.input_queue.put(data[3:])

    def run(self):
        print "connecting to", self.mac
        GATTRequester.connect(self, wait = True)
        print "connected. reading from handle", self.handle, "..."
        self.read_by_handle_async(self.handle, self.response)
        
        pos = 0
        block = StringIO()
        
        while True:
            data = None
            if pos == 0:
                # Create a new buffer and wait for data.  This can
                # only wait a few seconds in order to check for
                # BLE disconnection.
                try:
                    data = self.output_queue.get(block = True, timeout = 3.0)
                    if data is None: return
                except Queue.Empty:
                    data = None
            else:
                # We read less than 20 bytes.  Time out in 10ms to
                # send a short packet.
                try:
                    data = self.output_queue.get(block = True, timeout = 0.01)
                    if data is None: break
                except Queue.Empty:
                    data = None
            
            if data is None:
                # Poll timeout
                if not self.is_connected():
                    print "not connected in run()"
                    self.input_queue.put(None)
                    break

                if pos == 0: continue # nothing to send

                self.write_by_handle_async(self.handle,
                    str(bytearray(block.getvalue())),
                    self.response)
                pos = 0
                block = StringIO()
            else:
                print "read:", len(data), "bytes"
                ipos = 0
                while ipos != len(data):
                    l = min(20 - pos, len(data) - ipos)
                    block.write(data[ipos:ipos + l])
                    ipos += l
                    pos += l
                    if pos == 20:
                        self.write_by_handle_async(self.handle,
                            block.getvalue(), self.response)
                        pos = 0
                        block = StringIO()

    def __del__(self):
        self.output_queue.put(None)
        self.input_queue.put(None)
        if self.thread is not None: self.thread.join()
        self.disconnect()

def is_hm10(address):
    req = GATTRequester(address, False)
    req.connect(True)
    characteristics = req.discover_characteristics()
    return [x['value_handle'] for x in characteristics
        if x['uuid'] == UART_CHARACTERISTIC]

def get_hm10_devices():
    service = DiscoveryService()
    ble_devices = service.discover(2)
    result = []
    for address, name in ble_devices.items():
        handle = is_hm10(address)
        if handle is not None:
            result.append((address, name, handle[0]))
    return result          
        