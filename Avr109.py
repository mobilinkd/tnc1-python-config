#!/usr/bin/env python2.7

import time
from struct import pack
from builtins import bytes

class Avr109(object):
    """AVR109 firmware upload protocol.  This currently just implements the
    limited subset of AVR109 (butterfly) protocol necessary to load the
    Atmega 328P used on the Mobilinkd TNC.
    """
    
    def __init__(self, reader, writer):
        self.sio_reader = reader
        self.sio_writer = writer
        
    def start(self):
        self.sio_writer.write(b'\033')
        self.sio_writer.flush()
        buf = self.sio_reader.read(10)
    
    def send_address(self, address):
        address //= 2 # convert from byte to word address
        ah = (address & 0xFF00) >> 8
        al = address & 0xFF
        self.sio_writer.write(bytes(pack('cBB', b'A', ah, al)))
        self.sio_writer.flush()
        self.verify_command_sent("Set address to: %04x" % address)
    
    def send_block(self, memtype, data):
        """Send a block of memory to the bootloader.  This command should
        be preceeded by a call to send_address() to set the address that
        the block will be written to.
        
        @note The block must be in multiple of 2 bytes (word size).
        
        @param memtype is the type of memory to write. 'E' is for EEPROM,
            'F' is for flash.
        @data is a block of data to be written."""
        
        assert(len(data) % 2 == 0)
        
        ah = 0
        al = len(data)
        
        self.sio_writer.write(bytes(pack('cBBc', b'B', ah, al, memtype)))
        self.sio_writer.write(data)
        self.sio_writer.flush()
        self.verify_command_sent("Block load: %d" % len(data))
    
    def read_block(self, memtype, size):
        """Read a block of memory from the bootloader.  This command should
        be preceeded by a call to send_address() to set the address that
        the block will be written to.
        
        @note The block must be in multiple of 2 bytes (word size).
        
        @param memtype is the type of memory to write. 'E' is for EEPROM,
            'F' is for flash.
        @param size is the size of the block to read."""
                
        self.sio_writer.write(bytes(pack('cBBc', b'g', 0, size, memtype)))
        self.sio_writer.flush()
        self.sio_reader.timeout = 1
        result = self.sio_reader.read(size)
        return result
        
    def write_block(self, address, memtype, data):
        pass
    
    def do_upload(self):
        pass
    
    def verify_command_sent(self, cmd):
        
        timeout = self.sio_reader.timeout
        self.sio_reader.timeout = 1
        c = self.sio_reader.read(1)
        self.sio_reader.timeout = timeout
        if c != b'\r':
            # Do not report c because it could be None
            raise IOError("programmer did not respond to command: %s" % cmd)
        else:
            pass
            # print "programmer success: %s" % cmd
    
    def chip_erase(self):
        time.sleep(.1)
        self.sio_writer.write(b'e')
        self.sio_writer.flush()
        self.verify_command_sent("chip erase")
    
    def enter_program_mode(self):
        time.sleep(.1)
        self.sio_writer.write(b'P')
        self.sio_writer.flush()
        self.verify_command_sent("enter program mode")
        
    def leave_program_mode(self):
        time.sleep(.1)
        self.sio_writer.write(b'L')
        self.sio_writer.flush()
        self.verify_command_sent("leave program mode")
   
    def exit_bootloader(self):
        time.sleep(.1)
        self.sio_writer.write(b'E')
        self.sio_writer.flush()
        self.verify_command_sent("exit bootloader")
        
    def supports_auto_increment(self):
        # Auto-increment support
        time.sleep(.1)
        self.sio_writer.write(b'a')
        self.sio_writer.flush()
        return (self.sio_reader.read(1) == b'Y')
    
    def get_block_size(self):
        
        time.sleep(.1)
        self.sio_writer.write(b'b')
        self.sio_writer.flush()
        if self.sio_reader.read(1) == b'Y':
            tmp = bytearray(self.sio_reader.read(2))
            return tmp[0] * 256 + tmp[1]
        return 0
   
    def get_bootloader_signature(self):
        
        self.sio_reader.timeout = 1
        junk = self.sio_reader.read()
        self.sio_reader.timeout = .1
        for i in range(10):
            self.start()
            # Bootloader
            self.sio_writer.write(b'S')
            self.sio_writer.flush()
            loader = self.sio_reader.read(7)
            if loader == b'XBoot++':
                return loader
            time.sleep(.1)
        raise RuntimeError("Invalid bootloader: {}".format(loader))
    
    def send_expect(self, cmd, expected, retries = 5):
        
        expected_len = len(expected)
        self.sio_reader.timeout = .1
        junk = self.sio_reader.read()
        for i in range(retries):
            self.sio_writer.write(cmd)
            self.sio_writer.flush()
            received = bytes(self.sio_reader.read(expected_len))
            if received == expected:
                return True
            time.sleep(.1)
        return False
        
    
    def get_software_version(self):
        """Return the bootloader software version as a string with the format
        MAJOR.MINOR (e.g. "1.7")."""

        time.sleep(.1)
        self.sio_writer.write(b'V')
        self.sio_writer.flush()
        self.sio_reader.timeout = .1
        sw_version = bytearray(bytes(self.sio_reader.read(2)))
        if len(sw_version) < 2: return "unknown"
        return "%d.%d" % (sw_version[0] - 48, sw_version[1] - 48)
    
    def get_programmer_type(self):
        
        return b'S' if self.send_expect(b'p', b'S') else None
        
        time.sleep(.1)
        self.sio_writer.write(b'p')
        self.sio_writer.flush()
        self.sio_reader.timeout = .1
        return self.sio_reader.read(1)
    
    def get_device_list(self):
        
        # Device Code
        self.sio_reader.timeout = .1
        self.sio_writer.write(b't')
        self.sio_writer.flush()
        device_list = []
        while True:
            device = bytearray(self.sio_reader.read(1))
            if device[0] == 0: break
            device_list.append(device)
        
        return device_list
        
    def get_device_signature(self):
        # Read Signature
        self.sio_writer.write(b's')
        self.sio_writer.flush()
        return self.sio_reader.read(3)

