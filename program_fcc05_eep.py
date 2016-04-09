from call_edriverdll import *
import time
from math import *
import sys
import re
import string
import struct
import ctypes

#    Steps to Load an EEPROM
#
#    0. Quiesce/halt firmware
#    1. Create an ICC packet for the EEP/FLASH/DATAFLASH Write
#    2. Write NVM Data into RAM Buffer 1
#    3. Poll for ICC complete
#    4. Trigger ICC operation
#    5. Write NVM Data into RAM Buffer 2
#    6. Poll for ICC complete
#    7. Trigger ICC operation
#    8. Goto 2 if not complete

############################################################
# Top level defines
############################################################

passwd_fcc3 = str(bytearray([0xC6, 0x6A, 0xA4, 0x66, 0xA0]))
passwd_fcc5 = str(bytearray([0xC5, 0x99, 0x89, 0x83, 0xE0]))

icc_cmd = {'nvm_rd': 0xA, 'nvm_wr': 0x9, 'nvm_cmd': 0x8, 'scr_rd': 0x6, 'scr_wr': 0x5,
           'ram_rd': 0x2, 'ram_wr': 0x1, 'ram_bc': 0x3, 'sys_cmd': 0xC}
nvm_dcc = {'wen': 6, 'wds': 4, 'rsr': 5, 'wsr': 1, 'r': 3, 'w': 2}

i2c_addr = 0xD0

i2c_addr_srch = [0xFE, 0xD2, 0xD0, 0xA2, 0xA0]

blksize = 0x10

#eepFile = open('qcdr-spi.pC0.v02.zc0401.fcc05-qcdr-1a.nvm.eep')
#eepFile = open('qcdr-spi.pC0.v03.zc0402.fcc05-qcdr-1a.nvm.eep')
#eepFile = open('qcdr-spi.pC0.v04.zc0402.fcc05-qcdr-1a.nvm.eep')
#eepFile = open(
#eepFile = open('qcdr-spi.pC0.v07.zc0405.fcc05-qcdr-1a.nvm.eep')

#eepFileName = 'qcdr-spi.pC0.v04.zc0402.fcc05-qcdr-1a.nvm.eep'
#eepFileName = 'qcdr-spi.pC0.v06.zc0404.fcc05-qcdr-1a.nvm.eep'
#eepFileName = 'qcdr-spi.pC0.v08.zc0406.fcc05-qcdr-1a.nvm.eep'
#eepFileName = 'qcdr-spi.pC0.v09.zc0407.fcc05-qcdr-1a.nvm.eep'
#eepFileName = 'qcdr-spi.pC0.v0A.zc0407.fcc05-qcdr-1a.nvm.eep'
#eepFileName = 'qcdr-spi.pC0.v0B.zc0408.fcc05-qcdr-1a.nvm.eep'
#eepFileName = 'qcdr-spi.pC0.v0C.zc0408.fcc05-qcdr-1a.nvm.eep'
#eepFileName = 'qcdr-spi.pC0.v0E.zc040A.fcc05-qcdr-1a.nvm.eep'
#eepFileName = 'qcdr-spi.pC0.v0F.zc040B.fcc05-qcdr-1a.nvm.eep'
eepFileName = 'qcdr-lp-spi_C1-04-2D-21_fcc06-qcdr-lp-1a.nvm.eep'

verbose = 0

############################################################
# Subroutines
############################################################

def toHexString(hexNum, length):
    length = length * 2
    foo = ''

    if type(hexNum) is str:
        #print 'already a string', hexNum
        foo = hexNum
    else:
        try:
            foo = hex(hexNum)
        except Exception, err:
            print 'ERROR:', str(err)

    if len(foo) > 0 and foo[-1] == 'L':
        foo = foo[:-1]

    if len(foo) > 2:
        foo = foo[2:]

    if len(foo) < length:
        foo = ('0'*(length - len(foo) )) + foo

    return foo

#----------------------------------------------------------------------------
#  get_nvm_tgt(target, autocmds, dryrun)
#    Target Byte:
#      TGT[7:6] = "01" = Master/Eslave with NVM select
#      TGT[5]   = 0 - No Dry Run, 1 - Dry Run
#      TGT[4]   = 0 - Enable Auto Cmds, 1 - Disable Auto Cmds
#      TGT[3:2] = "00" - Reserved
#      TGT[1]   = 0 - System, 1 - NVM
#      TGT[0]   = 0 - Master, 1 - Eslave
#----------------------------------------------------------------------------
def get_nvm_tgt (eslave, dsblautocmds, dryrun):
    target = 0x42
    if dsblautocmds == "dsbl_autocmds":
        target = target | 0x10
    if dryrun == "dryrun":
        target = target | 0x20
    if eslave == "eslave":
        target = target | 0x01
    return target

def init_comms():
    print 'Initializing Driver'
    #config I2C driver board
    result_c = 0
    try:
        result_c = edriver_config(error)
        #edriver_ini()
        #result_c = edriver_usb_dev_create(error)
    except Exception, err:
        print 'Exception: Driver config fail!', err
    if(result_c == 1):
        print 'Configured driver successfullly!'
    else:
        print 'Driver config fail!'
        print error.raw
    return result_c

def find_fcc(i2c_addr):
    #Find FCC I2C address
    #return i2c_addr
    for i2c_addr in i2c_addr_srch:
        result = edriver_i2c_write(i2c_addr,0x00,0,0,data_c,error)
        if(result == 1):
            break
    else:
        print "FCC I2C address not found!"
        return 0

    return i2c_addr

def halt_fcc():

    print 'Using I2C Address:', hex(i2c_addr)
    #write passwd_fcc5 to 0x7B-0x7F
    result = edriver_i2c_write(i2c_addr,0x7B,5,0,passwd_fcc5,error)
    data_c[0] = chr(0x21)
    result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)
    result = edriver_i2c_read(i2c_addr,0x92,1,0,data_c,error)
    print 'ES CID:', ord(data_c[0])
    result = edriver_i2c_read(i2c_addr,0x93,1,0,data_c,error)
    print 'My CID:', ord(data_c[0])
    #time.sleep(3)
    for i in range(100):
        result = edriver_i2c_read(i2c_addr,0x9F,1,0,data_c,error)
        #read back 0x1009F checking for 0x20
        if ord(data_c[0]) == 0x20:
            print 'Halted FCC'
            break
        #else:
            #print 'Waiting: ',  ord(data_c[0])

    # reset ICC bus
    data_c[0] = chr(0x01)
    result = edriver_i2c_write(i2c_addr,0xD7,1,0,data_c,error)

    wait_4_icc_idle()

#----------------------------------------------------------------------------
#  wait_4_icc_idle
#----------------------------------------------------------------------------
def wait_4_icc_idle ():

    # set page
    data_c[0] = chr(0x21)
    result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)

    for count in range(100):
        result = edriver_i2c_read(i2c_addr,0xDA,1,0,data_c,error)
        #print repr(data_c[0])
        if ord(data_c[0]) == 0 or ord(data_c[0]) == 0x02:
            break       # ICC is idle (or reserved)
    else:
        print 'Timeout error waiting for ICC_IDLE'

    return count

#----------------------------------------------------------------------------
#  icc_snd_pkt
#----------------------------------------------------------------------------
def icc_snd_pkt (pkt_addr):

    # set page
    #data_c[0] = chr(0x21)
    #result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)

    for count in range(100):
        #reserve ICC bus
        data_c[0] = chr(0x02)
        result = edriver_i2c_write(i2c_addr,0xDA,1,0,data_c,error)

        result = edriver_i2c_read(i2c_addr,0xDA,1,0,data_c,error)
        if ord(data_c[0]) == 0x02:
            break
    else:
        print 'Timeout error trying to reserve bus'
        return count

    # set page - ok
    #data_c[0] = chr(0x21)
    #result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)

    # Set ICC PacketGo
    data_c[0] = chr(0x03)
    result = edriver_i2c_write(i2c_addr,0xDA,1,0,data_c,error)

    return count

############################################################
# Main function
############################################################

error = create_string_buffer(200)
data_c = create_string_buffer(1)
pkt_addr = 0x0040
ram_addr = 0x0000
next_chunk_addr = chunk_addr = 0x00

if init_comms() != 1:
    exit()

# Get file name of EEP image from command line or internal default
if len(sys.argv) == 1:
    print 'Using default EEP file name:', eepFileName
elif len(sys.argv) == 2:
    eepFileName = sys.argv[1]
    print 'Programming EEP file:', eepFileName
else:
    print 'Invalid command line arguments'
    exit()

eepFile = open(eepFileName)

i2c_addr = find_fcc(i2c_addr)
if i2c_addr == 0:
    exit()

halt_fcc()

#setting NVM mode to EEPROM
# set page
data_c[0] = chr(0x21)
result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)

result = edriver_i2c_read(i2c_addr,0x87,1,0,data_c,error)
#if ord(data_c[0]) == 0x02:
#data_c[0] = chr(0x01)
data_c[0] = chr(( ord(data_c[0]) & 0x3F) | 0x40)
print 'NVM setting:', ord(data_c[0])
result = edriver_i2c_write(i2c_addr,0x87,1,0,data_c,error)

# Set ICC packetAddr
datastr = toHexString(pkt_addr, 2)
datastr = bytearray(datastr.decode("hex"))
mytype = ctypes.c_char * len(datastr)
dbuf = mytype.from_buffer(datastr)
#print pkt_addr, repr(datastr), repr(dbuf)
result = edriver_i2c_write(i2c_addr,0xD8,2,0,dbuf,error)


print "Programming FCC EEPROM"
#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-
next_chunk_addr = chunk_addr = 0x00
eep_data = ""

# parse the EEP file line by line, into one buffer
for line in eepFile:
    match = re.search(r'([0-9a-f]{3,5}):(.*$)', line.lower())
    if match:
        chunk_addr = int(match.group(1), 16)
        if chunk_addr != next_chunk_addr:
            print 'EEP File parse error, addresses not sequential:', hex(chunk_addr)
            exit()

        next_chunk_addr = chunk_addr + 0x10             # 16 bytes per line
        eep_data += ''.join(match.group(2).split())     # Add onto string

# Replace -- with 00
eep_data = eep_data.replace("--", "00")

start = 0
end = 0
blkSize = 0x20

while start < len(eep_data):
    end = start + blkSize * 2
    blk = bytearray.fromhex(eep_data[start:end])
    blk_len = len(blk)

    nvm_addr = start / 2

    if verbose:
        print "%04X"%(nvm_addr), ':', repr(blk[:8])

    # Write data buffer to RAM
    mytype = ctypes.c_char * len(blk)
    dbuf = mytype.from_buffer(blk)
    result = edriver_i2c_write(i2c_addr,ram_addr,blk_len,0,dbuf,error)
    if result != 1:
        print "ERROR Writing data buffer"
        exit()

    # Build ICC command packet
    tgt = get_nvm_tgt("master","autocmds","no_dryrun")
    datastr = toHexString(icc_cmd['nvm_wr'], 1) + toHexString(tgt, 1) + toHexString(nvm_dcc['w'], 1)
    datastr += toHexString(blk_len, 2) + toHexString(nvm_addr, 3) + toHexString(ram_addr, 2)
    datastr = bytearray(datastr.decode("hex"))

    # Write ICC command packet
    mytype = ctypes.c_char * len(datastr)
    dbuf = mytype.from_buffer(datastr)
    result = edriver_i2c_write(i2c_addr,pkt_addr,len(datastr),0,dbuf,error)
    if result != 1:
        print "ERROR Writing ICC packet"
        exit()

    #print 'Waiting for ICC Idle'
    wait_4_icc_idle()

    #print 'Sending ICC Packet'
    # Sending ICC Packet
    icc_snd_pkt(pkt_addr)

    #print 'Waiting for ICC Idle'
    #wait_4_icc_idle()

    start = end

    #print a series of .... to indicate progress
    sys.stdout.write('.')
    sys.stdout.flush()

#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-

print ''
print 'Done programming FCC EEPROM'
eepFile.close()
#reboot FCC

# set page
data_c[0] = chr(0x21)
result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)

print 'Rebooting. Ignore the following error: '
data_c[0] = chr(0x01)
result = edriver_i2c_write(i2c_addr,0xBF,1,0,data_c,error)

exit()
