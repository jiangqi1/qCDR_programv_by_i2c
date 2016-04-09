from call_edriverdll import *
import time
from math import *
import sys
import re
import string
import struct
import ctypes

error = create_string_buffer(200)
data_c = create_string_buffer(1)

i2c_addr = 0xFE

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

def init_comms():
    print 'Initializing Driver'
    #config I2C driver board
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

def list_i2c_addresses():
    found_device = False
    i2c_addr = 0x00
    while i2c_addr < 0xFF:
        result = edriver_i2c_write(i2c_addr,0x00,0,0,data_c,error)
        if(result == 1):
            print hex(i2c_addr)
            found_device = True
        i2c_addr = i2c_addr + 2

    if(found_device == False):
        print 'No I2C devices found'

#def read_block():
    #result = edriver_i2c_read(i2c_addr,0x00,0,0,data_c,error)


#----------------------------------------------------------------------------
if init_comms() != 1:
    exit()

list_i2c_addresses()
