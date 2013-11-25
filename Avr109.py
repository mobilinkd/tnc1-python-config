#!/usr/bin/env python2.7

class Avr109(object):
    """AVR109 firmware upload protocol.  This currently just implements the
    limited subset of AVR109 (butterfly) protocol necessary to load the
    Atmega 328P used on the Mobilinkd TNC.
    """
    
    def __init__(self, reader, writer):
        self.sio_reader = reader
        self.sio_writer = writer
        
    def start(self):
        self.sio_writer.write('\033')
        self.sio_writer.flush()
        buf = self.sio_reader.read(10)
        print buf
    
    def send_address(self, address):
        address /= 2 # convert from byte to word address
        ah = chr((address & 0xFF00) >> 8)
        al = chr(address & 0xFF)
        self.sio_writer.write('A' + ah + al)
        self.sio_writer.flush()
        self.verify_command_sent("Set address to: %x" % address)
    
    def send_block(self, memtype, data):
        """Send a block of memory to the bootloader.  This command should
        be preceeded by a call to send_address() to set the address that
        the block will be written to.
        
        @note The block must be in multiple of 2 bytes (word size).
        
        @param memtype is the type of memory to write. 'E' is for EEPROM,
            'F' is for flash.
        @data is a block of data to be written."""
        
        assert(len(data) % 2 == 0)
        
        ah = chr(0)
        al = chr(len(data))
        
        self.sio_writer.write('B' + ah + al + memtype)
        self.sio_writer.write("".join([chr(c) for c in data]))
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
        
        ah = chr(0)
        al = chr(size)
        
        self.sio_writer.write('g' + ah + al + memtype)
        self.sio_writer.flush()
        result = self.sio_writer.read(size)
        return [ord(c) for c in result]
        
    def write_block(self, address, memtype, data):
        pass
    
    def do_upload(self):
        pass
    
    def verify_command_sent(self, cmd):
        
        timeout = self.sio_reader.timeout
        self.sio_reader.timeout = 10
        c = self.sio_reader.read(1)
        self.sio_reader.timeout = timeout
        if c != '\r':
            # Do not report c because it could be None
            raise IOError("programmer did not respond to command: %s" % cmd)
        else:
            pass
            # print "programmer success: %s" % cmd
    
    def chip_erase(self):
        self.sio_writer.write('e')
        self.sio_writer.flush()
        self.verify_command_sent("chip erase")
    
    def enter_program_mode(self):
        self.sio_writer.write('P')
        self.sio_writer.flush()
        self.verify_command_sent("enter program mode")
        
    def leave_program_mode(self):
        self.sio_writer.write('L')
        self.sio_writer.flush()
        self.verify_command_sent("leave program mode")
   
    def exit_bootloader(self):
        self.sio_writer.write('E')
        self.sio_writer.flush()
        self.verify_command_sent("exit bootloader")
        
    def supports_auto_increment(self):
        # Auto-increment support
        self.sio_writer.write('a')
        self.sio_writer.flush()
        return (self.sio_reader.read(1) == 'Y')
    
    def get_block_size(self):
        
        self.sio_writer.write('b')
        self.sio_writer.flush()
        if self.sio_reader.read(1) == 'Y':
            tmp = self.sio_reader.read(2)
            return ord(tmp[0]) * 256 + ord(tmp[1])
        return 0
   
    def get_bootloader_signature(self):
        
        for i in range(10):
            self.start()
            # Bootloader
            self.sio_writer.write('S')
            self.sio_writer.flush()
            loader = self.sio_reader.read(7)
            if loader == 'XBoot++':
                return loader
        
        raise RuntimeError("Invalid bootloader: " + loader)
    
    def get_software_version(self):
        """Return the bootloader software version as a string with the format
        MAJOR.MINOR (e.g. "1.7")."""

        self.sio_writer.write('V')
        self.sio_writer.flush()
        sw_version = self.sio_reader.read(2)
        return "%d.%d" % (ord(sw_version[0]) - 48, ord(sw_version[1]) - 48)
    
    def get_programmer_type(self):
        
        self.sio_writer.write('p')
        self.sio_writer.flush()
        return self.sio_reader.read(1)
    
    def get_device_list(self):
        
        # Device Code
        self.sio_writer.write('t')
        self.sio_writer.flush()
        device_list = []
        while True:
            device = self.sio_reader.read(1)      
            if ord(device[0]) == 0: break
            device_list.append(device)
        
        return device_list
        
    def get_device_signature(self):
        # Read Signature
        self.sio_writer.write('s')
        self.sio_writer.flush()
        return self.sio_reader.read(3)

