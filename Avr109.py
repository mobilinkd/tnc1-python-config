#!/usr/bin/env python2.7

class Avr109(object):
    """AVR109 firmware upload protocol.  This currently just implements the
    limited subset of AVR109 (butterfly) protocol necessary to load the
    Atmega 328P used on the Mobilinkd TNC.
    """
    
    def __init__(self, reader, writer, filename):
        self.sio_reader = reader
        self.sio_writer = writer
        self.filename = filename
        
    def start(self):
        self.sio_writer.write('\033')
        self.sio_writer.flush()
        buf = self.sio_reader.read(10)
        print buf
    
    def do_upload(self):
        pass
    
    def verify_command_sent(self, cmd):
        c = self.sio_reader.read(1)
        if c != '\r':
            raise IOError("programmer did not respond to command: %s" % cmd)
    
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
   
    def initialize(self):
    
        loader = ""
        while loader != 'XBoot++':
            self.start()
            # Bootloader
            self.sio_writer.write('S')
            self.sio_writer.flush()
            loader = self.sio_reader.read(7)
            print "loader", loader
        
        # Software Version
        self.sio_writer.write('V')
        self.sio_writer.flush()
        sw_version = self.sio_reader.read(2)
        
        # Hardware Version
        self.sio_writer.write('V')
        self.sio_writer.flush()
        hw_version = self.sio_reader.read(2)
        
        # Programmer Type
        self.sio_writer.write('p')
        self.sio_writer.flush()
        programmer_type = self.sio_reader.read(1)
        
        # Auto-increment support
        self.sio_writer.write('p')
        self.sio_writer.flush()
        auto_increment = (self.sio_reader.read(1) == 'Y')
        
        # Block-mode support
        buffer_size = 0
        self.sio_writer.write('b')
        self.sio_writer.flush()
        auto_increment = (self.sio_reader.read(1) == 'Y')
        if auto_increment:
            tmp = self.sio_reader.read(2)
            buffer_size = ord(tmp[0]) * 256 + ord(tmp[1])
        
        # Device Code
        self.sio_writer.write('t')
        self.sio_writer.flush()
        device_list = []
        while True:
            device = self.sio_reader.read(1)      
            if ord(device[0]) == 0: break
            device_list.append(device)
        
        # Read Signature
        self.sio_writer.write('s')
        self.sio_writer.flush()
        signature = self.sio_reader.read(3)
 
        print "  Found programmer: Id = '%s'; type = '%s'" % (loader, programmer_type)
        print "  Software Version: %d.%d" % (ord(sw_version[0]) - 48, ord(sw_version[1]) - 48)
        print "  Hardware Version: %d.%d" % (ord(hw_version[0]) - 48, ord(hw_version[1]) - 48)
        print "Has auto-increment: %s" % (str(auto_increment))
        print "    Has block-mode: %s (size = %d)" % (str(auto_increment), buffer_size)
        print "  Device Signature: %02x %02x %02x" % (ord(signature[0]),ord(signature[1]),ord(signature[2]))
        
        if signature != '\x0f\x95\x1e':
            raise ValueError("Bad device signature. Not an AVR ATmega 328P.")
        
        # Select Device
        self.sio_writer.write('T' + device_list[0])
        self.sio_writer.flush()
        self.sio_reader.read(1)

