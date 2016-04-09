from call_edriverdll import *
import time
from math import *
import sys
import re
import string
import struct
import ctypes
import random

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
passwd_fcc5 = str(bytearray([0xC5, 0x99, 0x89, 0x83, 0xE0]))

icc_cmd = {'nvm_rd': 0xA, 'nvm_wr': 0x9, 'nvm_cmd': 0x8, 'scr_rd': 0x6, 'scr_wr': 0x5,
           'ram_rd': 0x2, 'ram_wr': 0x1, 'ram_bc': 0x3, 'sys_cmd': 0xC}
nvm_dcc = {'wen': 6, 'wds': 4, 'rsr': 5, 'wsr': 1, 'r': 3, 'w': 2}

i2c_addr = 0xD0

num_qCDRs = 5

i2c_addr_srch = [0xFE, 0xD2, 0xD0]

verbose = 0

pkt_addr = 0x0040 # ICC packet address
ram_addr = 0x0000 # RAM buffer address

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
    print 'initializing Driver'
    #config I2C driver board
    try:
        result_c = edriver_config(error)
        #edriver_ini()
        #result_c = edriver_usb_dev_create(error)
    except Exception, err:
        print 'Driver config threw exception!', err
    if(result_c == 1):
        print 'Configured driver successfullly!'
    else:
        print 'Driver config fail!'
    return result_c

def find_fcc(i2c_addr):
    #Find FCC I2C address
    #return i2c_addr
    for i2c_addr in i2c_addr_srch:
        result = edriver_i2c_write(i2c_addr,0x00,0,0,data_c,error)
        if(result == 1):
            break
    else:
        print "qCDR Not Found!"
        return 0

    return i2c_addr

def halt_fcc():

    print 'Using I2C Address:', hex(i2c_addr)
    #write passwd_fcc5 to 0x7B-0x7F
    result = edriver_i2c_write(i2c_addr,0x7B,5,0,passwd_fcc5,error)

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

    for count in range(200):
        result = edriver_i2c_read(i2c_addr,0xDA,1,0,data_c,error)
        #print repr(data_c[0])
        if ord(data_c[0]) == 0 or ord(data_c[0]) == 0x02:
            break       # ICC is idle (or reserved)
    else:
        quit_failure('Timeout error waiting for ICC_IDLE')

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
        quit_failure('Timeout error trying to reserve bus')

    # set page - ok
    #data_c[0] = chr(0x21)
    #result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)

    # Set ICC PacketGo
    data_c[0] = chr(0x03)
    result = edriver_i2c_write(i2c_addr,0xDA,1,0,data_c,error)

    return count

#----------------------------------------------------------------------------
def quit_failure(err_msg):
    print err_msg
    print "----------------------------"
    print "qCDR and EEPROM test FAILED!"

    print "Press enter to continue..."
    sys.stdin.read(1)
    exit()

#----------------------------------------------------------------------------
def get_qCDR_type(tgt):
    read_data = ''

    length = 0x04
    scr_addr = 0x0004
    datastr = toHexString(icc_cmd['scr_rd'], 1) + toHexString(tgt, 1) + toHexString(scr_addr, 2)
    datastr += toHexString(0, 1) + toHexString(length-1, 1) + toHexString(ram_addr, 2)
    datastr = bytearray(datastr.decode("hex"))

    # Write ICC command packet
    mytype = ctypes.c_char * len(datastr)
    dbuf = mytype.from_buffer(datastr)
    result = edriver_i2c_write(i2c_addr,pkt_addr,len(datastr),0,dbuf,error)
    if result != 1:
        quit_failure("ERROR Writing ICC packet")

    icc_snd_pkt(pkt_addr)

    #print 'Waiting for ICC Idle'
    wait_4_icc_idle()

    # Read Data data buffer from RAM
    #mytype = ctypes.c_char * length
    dbuf = ctypes.create_string_buffer(length)
    result = edriver_i2c_read(i2c_addr,ram_addr,length,0,dbuf,error)
    if result != 1:
        quit_failure("ERROR reading data buffer")

    read_data = bytearray(dbuf[i] for i in range(length))

    #print len(read_data), repr(read_data)

    return read_data

#----------------------------------------------------------------------------
#  EEPROM Read
#----------------------------------------------------------------------------

def eeprom_read (nvm_addr, length):
    read_data = ''

    # Build ICC command packet
    tgt = get_nvm_tgt("master","autocmds","no_dryrun")
    datastr = toHexString(icc_cmd['nvm_rd'], 1) + toHexString(tgt, 1) + toHexString(nvm_dcc['r'], 1)
    datastr += toHexString(length, 2) + toHexString(nvm_addr, 3) + toHexString(ram_addr, 2)
    datastr = bytearray(datastr.decode("hex"))

    # Write ICC command packet
    mytype = ctypes.c_char * len(datastr)
    dbuf = mytype.from_buffer(datastr)
    result = edriver_i2c_write(i2c_addr,pkt_addr,len(datastr),0,dbuf,error)
    if result != 1:
        quit_failure("ERROR Writing ICC packet")

    #print 'Sending ICC Packet'
    icc_snd_pkt(pkt_addr)

    #print 'Waiting for ICC Idle'
    wait_4_icc_idle()

    # Read Data data buffer from RAM
    #mytype = ctypes.c_char * length
    dbuf = ctypes.create_string_buffer(length*2)
    result = edriver_i2c_read(i2c_addr,ram_addr,length,0,dbuf,error)
    if result != 1:
        quit_failure("ERROR Writing data buffer")

    read_data = bytearray(dbuf[i] for i in range(length))

    #print len(read_data), repr(read_data)

    return read_data

#----------------------------------------------------------------------------
#  EEPROM Write
#----------------------------------------------------------------------------
def eeprom_write (blk, nvm_addr, length):
    if (len(blk) < length):
        print "length exceeds data length"
        return 0

    # Write data buffer to RAM
    mytype = ctypes.c_char * len(blk)
    dbuf = mytype.from_buffer(blk)
    result = edriver_i2c_write(i2c_addr,ram_addr,length,0,dbuf,error)
    if result != 1:
        print "ERROR Writing data buffer"
        exit()

    # Build ICC command packet
    tgt = get_nvm_tgt("master","autocmds","no_dryrun")
    datastr = toHexString(icc_cmd['nvm_wr'], 1) + toHexString(tgt, 1) + toHexString(nvm_dcc['w'], 1)
    datastr += toHexString(length, 2) + toHexString(nvm_addr, 3) + toHexString(ram_addr, 2)
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

    return length


############################################################
# Main function
############################################################
error = create_string_buffer(200)
data_c = create_string_buffer(1)

if init_comms() != 1:
    exit()

# Get file name of EEP image from command line or internal default

i2c_addr = find_fcc(i2c_addr)
if i2c_addr == 0:
    exit()

halt_fcc()

# Check End Slave Chip ID
data_c[0] = chr(0x21)
result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)
result = edriver_i2c_read(i2c_addr,0x92,1,0,data_c,error)
if ord(data_c[0]) != num_qCDRs:
    print 'Incorrect number of qCDRs found! (ES CID = ', ord(data_c[0]), ')'
    exit()
else:
    print 'Correct number of qCDRs found. (ES CID = ', ord(data_c[0]), ')'


#setting NVM mode to EEPROM
# set page
data_c[0] = chr(0x21)
result = edriver_i2c_write(i2c_addr,0x7F,1,0,data_c,error)

result = edriver_i2c_read(i2c_addr,0x87,1,0,data_c,error)
#if ord(data_c[0]) == 0x02:
#data_c[0] = chr(0x01)
data_c[0] = chr(( ord(data_c[0]) & 0x3F) | 0x40)
#print 'NVM setting:', ord(data_c[0])
result = edriver_i2c_write(i2c_addr,0x87,1,0,data_c,error)

# Set ICC packetAddr
datastr = toHexString(pkt_addr, 2)
datastr = bytearray(datastr.decode("hex"))
mytype = ctypes.c_char * len(datastr)
dbuf = mytype.from_buffer(datastr)
#print pkt_addr, repr(datastr), repr(dbuf)
result = edriver_i2c_write(i2c_addr,0xD8,2,0,dbuf,error)

# Get qCDR types
for x in range(num_qCDRs):
    qcdr_ver = get_qCDR_type(x+1)

    # qCDR minor type
    if qcdr_ver[1] == 1:
        chip_type_min = '28G'
    elif qcdr_ver[1] == 2:
        chip_type_min = '!!20G!!'
    else:
        chip_type_min = 'UNKNOWN'

    # Check minor rev
    if qcdr_ver[3] == 1:
        chip_ver_min = 'A'
    elif qcdr_ver[3] == 2:
        chip_ver_min = 'B'
    else:
        chip_ver_min = 'U'

    print x+1, ':', 'qCDR', chip_type_min, qcdr_ver[2], chip_ver_min

exit()


print "Checking EEPROM"
#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-
eep_data = ''.join(str(random.randint(0,9)) for x in range(16))

blk = bytearray.fromhex(eep_data)
save_data = eeprom_read(0, 8)
eeprom_write(blk, 0, 8)
read_data = eeprom_read(0, 8)
eeprom_write(save_data, 0, 8)

if (read_data == blk):
    print "EEPROM test OK"
else:
    quit_failure("Error: EEPROM Readback Failed")

print "-----------------------"
print "qCDR and EEPROM Test PASSED!"

print "Press enter to continue..."
sys.stdin.read(1)
exit()

