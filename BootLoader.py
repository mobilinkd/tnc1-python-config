#!/bin/env python2.7
#
# Copyright (c) 2013 Mobilinkd LLC. All Rights Reserved.
# Released under the Apache License 2.0.

from IntelHexRecord import IntelHexRecord
from Avr109 import Avr109

import time
import sys
import os

class FirmwareSegment(object):
    
    def __init__(self, memory_type, address, data):
        
        self.memory_type = memory_type
        self.address = address
        self.data = data
    
    def __len__(self):
        return len(self.data)
    
    def __repr__(self):
        return "%s: type(%s), len(%d)" % \
            (self.__class__.__name__, self.memory_type, len(self.data))

class Firmware(object):
    
    def __init__(self, filename):
        
        self.filename = filename
        self.segments = []
        self.load()
    
    def load(self):
        
        address = 0
        data = []
        for line in file(self.filename):
            record = IntelHexRecord(line.strip())
            
            if record.recordType == 1:
                break
            
            if record.address != address:
                if len(data) > 0:
                    segment = FirmwareSegment('F', address - len(data), data)
                    self.segments.append(segment)
                    data = []
                address = record.address
            
            data += record.data
            address += record.byteCount
        
        segment = FirmwareSegment('F', address - len(data), data)
        self.segments.append(segment)
    
    def __len__(self):
        
        size = 0
        for segment in self.segments:
            size += len(segment)
        
        return size
    
    def __iter__(self):
        
        for segment in self.segments:
            yield segment

class BootLoader(object):
    
    def __init__(self, reader, writer, filename, gui = None):
        self.avr109 = None
        self.reader = reader
        self.firmware = Firmware(filename)
        self.gui = gui
        self.avr109 = Avr109(reader, writer)
        self.initialize()
        self.block = []
        self.address = 0
        if self.gui is not None:
            self.gui.set_steps(len(self.firmware) / self.block_size)
    
    def __del__(self):
        if self.avr109 is not None:
            self.exit()
    
    def initialize(self):
    
        self.loader = self.avr109.get_bootloader_signature()
        self.programmer_type = self.avr109.get_programmer_type()
        self.sw_version = self.avr109.get_software_version()
        self.auto_increment = self.avr109.supports_auto_increment()
        self.block_size = self.avr109.get_block_size()
        self.device_list = self.avr109.get_device_list()
        self.signature = self.avr109.get_device_signature()
 
        #         print "  Found programmer: Id = '%s'; type = '%s'" % (self.loader, self.programmer_type)
        #         print "Programmer Version: %s" % self.sw_version
        #         print "Has auto-increment: %s" % (str(self.auto_increment))
        #         print "    Has block-mode: %s (size = %d)" % (str(self.block_size > 0), self.block_size)
        #         print "  Device Signature: %02x %02x %02x" % (ord(self.signature[0]),ord(self.signature[1]),ord(self.signature[2]))
        
        if self.signature != '\x0f\x95\x1e':
            self.avr109.exit_bootloader()
            raise ValueError("Bad device signature. Not an AVR ATmega 328P.")
        if not self.auto_increment:
            self.avr109.exit_bootloader()
            raise ValueError("Bootloader does not support auto-increment")
        if self.block_size != 128:
            self.avr109.exit_bootloader()
            raise ValueError("Unexpected block size")
    
    def chip_erase(self):
        
        self.avr109.enter_program_mode()
        self.avr109.chip_erase()
        self.avr109.leave_program_mode()
   
    def set_address(self, address):
        
        # print "Setting address %x" % address
        self.avr109.send_address(address)
    
    def load(self):
        
        if self.gui is not None:
            self.gui.writing()
            
        try:
            self.avr109.enter_program_mode()
            for segment in self.firmware:
                self.set_address(segment.address)
                pos = 0
                size = len(segment)
                while pos < size:
                    tmp = segment.data[pos:pos + self.block_size]
                    # print "sending %04x" % (pos + segment.address)
                    self.avr109.send_block('F', tmp)
                    pos += self.block_size
                    if self.gui is not None:
                        self.gui.pulse()

        except Exception as e:
            # app.exception(e)
            self.avr109.chip_erase()
            print(e)

        finally:
            self.avr109.leave_program_mode()


    def verify(self):
        
        if self.gui is not None:
            self.gui.verifying()
            
        try:
            for segment in self.firmware:
                self.set_address(segment.address)
                pos = 0
                size = len(segment)
                while pos < size:
                    tmp = segment.data[pos:pos + self.block_size]
                    # print "reading %04x" % (pos + segment.address)
                    block = self.avr109.read_block('F', len(tmp))
                    if tmp != block:
                        raise IOError(
                            "verify failed at %04X" % (pos + segment.address))
                    pos += self.block_size
                    if self.gui is not None:
                        self.gui.pulse()

        except Exception as e:
            # app.exception(e)
            self.chip_erase()
            return False
        
        return True
    
    def exit(self):
        self.avr109.exit_bootloader()
        self.avr109 = None

if __name__ == '__main__':
    
    import sys, os
    import serial
    
    if len(sys.argv) < 3:
        print("Usage: %s <device> <intel hex image file>")
        sys.exit(1)
    
    device = sys.argv[1]
    if not os.path.exists(device):
        print("%s does not exist")
        sys.exit(1)
    
    filename = sys.argv[2]
    if not os.path.exists(filename):
        print("%s does not exist")
        sys.exit(1)

    ser = serial.Serial(device, 115200, timeout=.1)
    loader = BootLoader(ser, ser, filename)
    loader.load()
    verified = loader.verify()
    if not verified:
        loader.chip_erase()
        pass

    