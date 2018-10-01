"""from tc08usb import TC08USB, USBTC08_ERROR, USBTC08_UNITS, USBTC08_TC_TYPE

tc08usb = TC08USB()
tc08usb.open_unit()
tc08usb.set_mains(50)
for i in range(1, 2):
    tc08usb.set_channel(i, USBTC08_TC_TYPE.K)
tc08usb.get_single()
tc08usb.close_unit()
for i in range(0, 2):
    print("%d: %f" % (i, tc08usb[i]))"""
    
import ctypes
import numpy as np
#from ctypes import *
mydll = ctypes.windll.LoadLibrary('usbtc08.dll')
device = mydll.usb_tc08_open_unit()
mydll.usb_tc08_set_mains(device,1)

temp = np.zeros( (9,), dtype=np.float32)
_overflow_flags=ctypes.c_int16()

mydll.usb_tc08_set_channel(device, 0, 0 )
tc_type=ord('K')
for i in range(0,9):
    mydll.usb_tc08_set_channel(device,i,tc_type)
mydll.usb_tc08_get_single(device, 
                          temp.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                          ctypes.byref(_overflow_flags),
                          0)
print(_overflow_flags.value)
mydll.usb_tc08_close_unit(device)
print(temp, _overflow_flags.value)

