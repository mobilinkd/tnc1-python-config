#!/usr/bin/env python2.7

from builtins import bytes
import time
import select

class SocketReader(object):
    
    def __init__(self, sock):
        
        self.sock = sock
        self.sock.setblocking(0)
        self.timeout = 5.0
    
    def recv(self, size = 512):
        
        start = time.time()
        data = bytearray(bytes())
        self.sock.settimeout(self.timeout)
        while self.timeout is None or start + self.timeout > time.time():
            ready = select.select([self.sock], [], [], self.timeout)
            if ready[0]:
                data += self.sock.recv(size - len(data))
                if len(data) == size: return data
            else:
                print("timed out")
        
        return data

class SocketWriter(object):
    
    def __init__(self, sock):
        
        self.sock = sock
        self.timeout = 5.0
    
    def send(self, data):
        
        print("sending %d bytes" % len(data))
        
        total = 0
        start = time.time()
        self.sock.setblocking(1)
        self.sock.settimeout(self.timeout)
        while (self.timeout is None or start + self.timeout > time.time()) and total != len(data):
            ready = select.select([], [self.sock], [], self.timeout)
            if ready[1]:
                total += self.sock.send(data[total:])

        self.sock.setblocking(0)

    
    

class Avr109(object):
    """AVR109 firmware upload protocol.  This currently just implements the
    limited subset of AVR109 (butterfly) protocol necessary to load the
    Atmega 328P used on the Mobilinkd TNC.
    """
    
    def __init__(self, reader, writer):
        self.sio_reader = SocketReader(reader)
        self.sio_writer = SocketWriter(writer)
        
    def start(self):
        self.sio_writer.send(bytes(b'\033'))
        
        buf = self.sio_reader.recv(10)
    
    def send_address(self, address):
        address //= 2 # convert from byte to word address
        ah = (address & 0xFF00) >> 8
        al = address & 0xFF
        self.sio_writer.send(bytes([b'A', ah, al]))
        
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
        
        e = None
        
        for _ in range(5):
            try:
                self.sio_writer.send(bytes([b'B', ah, al, memtype]))
                self.sio_writer.send(data)
                self.verify_command_sent("Block load: %d" % len(data))
                return
            except Exception as ex:
                print(ex)
                e = ex
        else:
            if e is not None: raise e
    
    def read_block(self, memtype, size):
        """Read a block of memory from the bootloader.  This command should
        be preceded by a call to send_address() to set the address that
        the block will be written to.
        
        @note The block must be in multiple of 2 bytes (word size).
        
        @param memtype is the type of memory to write. 'E' is for EEPROM,
            'F' is for flash.
        @param size is the size of the block to read."""
                
        self.sio_writer.send(bytes([b'g', 0, size, memtype]))
        
        self.sio_reader.timeout = 5.0
        result = self.sio_reader.recv(size)
        return result
        
    def write_block(self, address, memtype, data):
        pass
    
    def do_upload(self):
        pass
    
    def verify_command_sent(self, cmd):
        
        timeout = self.sio_reader.timeout
        self.sio_reader.timeout = 5.0
        c = self.sio_reader.recv(1)
        self.sio_reader.timeout = timeout
        if c != bytes(b'\r'):
            # Do not report c because it could be None
            raise IOError("programmer did not respond to command: %s (%d: %s)" % (cmd, len(c), str(c)))
        else:
            pass
            print("programmer success: %s" % cmd)
    
    def chip_erase(self):
        time.sleep(.1)
        self.sio_writer.send(bytes(b'e'))
        
        self.verify_command_sent("chip erase")
    
    def enter_program_mode(self):
        time.sleep(.1)
        self.sio_writer.send(bytes(b'P'))
        
        self.verify_command_sent("enter program mode")
        
    def leave_program_mode(self):
        time.sleep(.1)
        self.sio_writer.send(bytes(b'L'))
        
        self.verify_command_sent("leave program mode")
   
    def exit_bootloader(self):
        time.sleep(.1)
        self.sio_writer.send(bytes(b'E'))
        
        self.verify_command_sent("exit bootloader")
        
    def supports_auto_increment(self):
        # Auto-increment support
        time.sleep(.1)
        self.sio_writer.send(bytes(b'a'))
        
        return (self.sio_reader.recv(1) == bytes(b'Y'))
    
    def get_block_size(self):
        
        time.sleep(.1)
        self.sio_writer.send(bytes(b'b'))
        
        if self.sio_reader.recv(1) == bytes(b'Y'):
            tmp = self.sio_reader.recv(2)
            return tmp[0] * 256 + tmp[1]
        return 0
   
    def get_bootloader_signature(self):
        
        self.sio_reader.timeout = 1
        junk = self.sio_reader.recv(512)
        self.sio_reader.timeout = .1
        for i in range(10):
            self.start()
            # Bootloader
            self.sio_writer.send(bytes(b'S'))
            
            loader = self.sio_reader.recv(7)
            if loader == bytes(b'XBoot++'):
                return loader
            time.sleep(.1)
        raise RuntimeError("Invalid bootloader: {}".format(loader))
    
    def send_expect(self, cmd, expected, retries = 5):
        
        expected_len = len(expected)
        self.sio_reader.timeout = .1
        junk = self.sio_reader.recv(512)
        for i in range(retries):
            self.sio_writer.send(cmd)
            
            received = self.sio_reader.recv(expected_len)
            if received == expected:
                return True
            time.sleep(.1)
        return False
        
    
    def get_software_version(self):
        """Return the bootloader software version as a string with the format
        MAJOR.MINOR (e.g. "1.7")."""

        time.sleep(.1)
        self.sio_writer.send(bytes(b'V'))
        
        self.sio_reader.timeout = .1
        sw_version = self.sio_reader.recv(2)
        if len(sw_version) < 2: return "unknown"
        return "%d.%d" % (sw_version[0] - 48, sw_version[1] - 48)
    
    def get_programmer_type(self):
        
        return bytes(b'S') if self.send_expect(bytes(b'p'), bytes(b'S')) else None
        
        time.sleep(.1)
        self.sio_writer.send(bytes(b'p'))
        
        self.sio_reader.timeout = .1
        return self.sio_reader.recv(1)
    
    def get_device_list(self):
        
        # Device Code
        self.sio_reader.timeout = .1
        self.sio_writer.send(bytes(b't'))
        
        device_list = []
        while True:
            device = self.sio_reader.recv(1)      
            if device[0] == 0: break
            device_list.append(device)
        
        return device_list
        
    def get_device_signature(self):
        # Read Signature
        self.sio_writer.send(bytes(b's'))
        return self.sio_reader.recv(3)

