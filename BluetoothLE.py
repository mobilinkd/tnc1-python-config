'''
Created on Aug 30, 2017

@author: rob
'''

from bluetooth.ble import DiscoveryService
from bluetooth.ble import GATTRequester, GATTResponse

import binascii
import Queue
import threading
import struct

from time import sleep
from cStringIO import StringIO

KTS_SERVICE_UUID = '424a0001-90d6-4c48-b2aa-ab415169c333'
KTS_RX_CHAR_UUID = '424a0002-90d6-4c48-b2aa-ab415169c333' # Read/Notify
KTS_TX_CHAR_UUID = '424a0003-90d6-4c48-b2aa-ab415169c333' # Write/Response


class Finder(GATTRequester):
    
    def __init__(self, address, connect = False):
        GATTRequester.__init__(self, address, connect)
        self.connect(True, channel_type = 'random', security_level = 'medium')
    
    def on_indication(self, handle, data):
        pass

def is_device_with_service(address, uuid):
    result = False
    try:
        finder = Finder(address, False)
        services = finder.discover_primary()
        for service in services:
            # print(service)
            if service['uuid'] == uuid: result = True
    except Exception:
        pass
    
    return result

def find_devices_with_service(uuid):

    service = DiscoveryService('hci0')
    devices = service.discover(2)
    
    results = []
    
    for address, name in devices.items():
        if is_device_with_service(address, uuid):
            if name == "": name = "TNC5"
            results.append((address, name))
    
    return results

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

    def __init__(self, mac, to_tnc, from_tnc, callback):
        self.thread = None
        self.mac = mac
        self.input_queue = from_tnc
        self.output_queue = to_tnc
        self.callback = callback
        self.response = TNCResponse(callback)
        GATTRequester.__init__(self, mac, False)

    def connect(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def find_characteristics(self):

        # Find the READ and WRITE characteristics and store their handles.
        chars = self.discover_characteristics()
        
        rx_handle = [x['value_handle'] for x in chars
            if x['uuid'] == KTS_RX_CHAR_UUID]
        tx_handle = [x['value_handle'] for x in chars
            if x['uuid'] == KTS_TX_CHAR_UUID]

        if len(rx_handle) != 0:
            self.rx_handle = rx_handle[0]
            self.rx_cccd = self.rx_handle + 1

        if len(tx_handle) != 0:
            self.tx_handle = tx_handle[0]

        if self.rx_handle is None or self.tx_handle is None:
            raise RuntimeError("TNC characteristics not found.")

    def enable_notification(self):
        
        print("enable notifications")
        self.write_by_handle(
            self.rx_cccd, struct.pack('<bb', 0x01, 0x00))

    def disable_notification(self):
               
        print("disable notifications")
        self.write_by_handle(
            self.rx_cccd, struct.pack('<bb', 0x00, 0x00))

    def write(self, data):
        self.output_queue.put(data)

    def on_notification(self, handle, data):
        # print "notified!"
        self.input_queue.put(data[3:])

    def on_indication(self, handle, data):
        pass

    def run(self):
        print "connecting to", self.mac
        GATTRequester.connect(self, wait=True, channel_type = 'random', security_level = 'medium')

        self.blocksize = 20 # Adjust per MTU

        self.find_characteristics()
        self.enable_notification()
        
        self.callback()
        
        block = StringIO()
        
        while True:
            data = None
            # Create a new buffer and wait for data.  This can
            # only wait a few seconds in order to check for
            # BLE disconnection.
            try:
                data = self.output_queue.get(block = True, timeout = 1.0)
                if data is None:
                    return
            except Queue.Empty:
                if not self.is_connected():
                    return
                continue
                        
            else:
                print("tx[{:2d}]: {}".format(len(data), binascii.hexlify(data)))
                
                for block in [data[i:i + self.blocksize] for i in range(0, len(data), self.blocksize)]:
                    print("tx[{:2d}]: {}".format(len(data), binascii.hexlify(block)))
                    self.write_by_handle_async(self.tx_handle, block, self.response)
                self.output_queue.task_done()
                

    def __del__(self):
        self.output_queue.put(None)
        self.input_queue.put(None)
        if self.thread is not None: self.thread.join()
        self.disable_notification()
        self.disconnect()


        