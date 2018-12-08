#!/bin/env python2.7

"""
http://en.wikipedia.org/wiki/Intel_HEX
"""

class IntelHexRecord(object):
    
    def __init__(self, line):
        
        self.parse(line)
        
    def hasValidStartCode(self, line):
        
        return line[0] == ':'
    
    def getByteCount(self, line):
        
        byteCount = int(line[1:3], 16);
        assert(byteCount < 256)
        return byteCount
    
    def getAddress(self, line):
        
        address = int(line[3:7], 16);
        assert(address < 65536)
        return address
    
    def getRecordType(self, line):
        
        recordType = int(line[7:9], 16)
        assert(recordType < 6)
        return recordType
    
    def getData(self, line, byteCount):
        
        data = bytearray()
        for i in range(9, 9 + byteCount * 2, 2):
            byte = int(line[i:i+2], 16)
            assert(byte < 256)
            data.append(byte)
        
        assert(len(data) == byteCount)
        return data
    
    def getChecksum(self, line):
        
        checksum = int(line[-2:], 16)
        assert(checksum < 256)
        return checksum
    
    def computeChecksum(self, line):
        
        data = [int(line[x:x+2], 16) for x in range(1,len(line)-2, 2)]
        checksum = 0
        for x in data:
            checksum += x
        
        checksum %= 256
        checksum = 256 - checksum
        checksum %= 256
        
        return checksum
    
    def isValid(self, line):
        
        return self.getChecksum(line) == self.computeChecksum(line)
    
    def parse(self, line):
        
        if not self.hasValidStartCode(line):
            raise IOError("invalid ihex format: '" + line + "'")
        
        self.byteCount = self.getByteCount(line)
        self.address = self.getAddress(line)
        self.recordType = self.getRecordType(line)
        self.data = self.getData(line, self.byteCount)
        self.checksum = self.getChecksum(line)
        
        if not self.isValid(line):
            raise IOError("checksum mismatch: '" + line + "'")
        
    
    def __repr__(self):
        
        return "%s:\n\tRecord Type: %x\n\t    Address: %x\n\t     Length: %d\n\t   Checksum: %x" % \
            (self.__class__.__name__, self.recordType, self.address, self.byteCount, self.checksum)

class IHexParser(object):
    
    def __init__(self, input):
        
        self.input = input
    
    def __next__(self):
        
        for line in self.input:
            record = IntelHexRecord(line.strip())
            yield record
        

if __name__ == "__main__":
    
    import sys
    
    line = ":100000000C949C010C94C5010C94C5010C94C50181"
    record = IntelHexRecord(line)
    print((record.byteCount))
    print((record.address))
    print((record.recordType))
    print((record.data))
    print((record.checksum))
    print((record.computeChecksum(line)))
    
    # 00 Checksum
    line = ":1008D0009FBF2FEF3FEF25C06FB7F89442A153A100"
    record = IntelHexRecord(line)
    print((record.byteCount))
    print((record.address))
    print((record.recordType))
    print((record.data))
    print((record.checksum))
    print((record.computeChecksum(line)))
    
    filename = "/home/rob/mobilinkd-tnc1/images/mobilinkd-286.hex"
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    
    for line in file(filename):
        record = IntelHexRecord(line.strip())
        print(record)
        
