from ctypes import *

edriver = windll.LoadLibrary("edriverdll.dll")

def edriver_usb_dev_create(error):
    result = edriver.dll_edriver_eui_usb_device_create(error)
    return result

def edriver_usb_dev_delete():
    result = edriver.dll_edriver_eui_usb_device_delete()
    return result

def edriver_test(num):
    result = edriver.dll_edriver_test(num)
    print num
    return result

def edriver_config(error):
    result = edriver.dll_edriver_config("QSFP",error)
    return result

def edriver_ini():
    result = edriver.dll_edriver_ini()
    return result

def edriver_version(version):
    result = edriver.dll_edriver_version(version)
    print version
    return result

def edriver_conn_version(data,error):
    result = edriver.dll_edriver_conn_version(data,error)
    print data
    print error
    return result

def edriver_i2c_write(dev,addr,num,delay,data,error):
    result = edriver.dll_edriver_i2c_write(dev,addr,num,delay,data,error)
    #print "Return data is: "+ str(data[0])
    #if result != 1:
    #    print "The error is: "+ str(error),". result = ",result
    #print result
    return result

def edriver_i2c_read(dev,addr,num,delay,data,error):
    result = edriver.dll_edriver_i2c_read(dev,addr,num,delay,data,error)
    #print "Return data is: "+ str(hex(data[0]))
    #if result != 1:
    #    print "The error is: "+ str(error),". result = ",result
    #print result
    return result
