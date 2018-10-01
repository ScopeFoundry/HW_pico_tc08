from ScopeFoundry.hardware import HardwareComponent
import numpy as np
from enum import Enum
import threading
import time
import ctypes

class PicoTC08_HW(HardwareComponent):
    
    """Details of ctypes interaction from  https://www.picotech.com/support/topic10247.html"""

    name = "pico_tc08"

    def __init__(self, app, debug=False, name=None, chan_names=None):
        if chan_names == None:
            chan_names = ["CJ"] + ["TC{}".format(i) for i in range(1,9)]
        self.chan_names = chan_names
        HardwareComponent.__init__(self, app, debug, name)
    
    def setup(self):
        
        self.settings.New("update_time", dtype=float, unit='s', initial=1.0)
        
        for i, chan_name in enumerate(self.chan_names):
            if chan_name == "_":
                continue
            self.settings.New(chan_name, dtype=float, unit="C")
            
    
    def connect(self):
#         from .tc08usb import TC08USB, USBTC08_ERROR, USBTC08_UNITS, USBTC08_TC_TYPE
# 
#         tc08usb = TC08USB()
#         tc08usb.open_unit()
#         tc08usb.set_mains(60)
#         
#         for i in range(1, 2):
#             tc08usb.set_channel(i, USBTC08_TC_TYPE.K)
        #tc08usb.get_single()
        #tc08usb.close_unit()
        #for i in range(0, 2):
        #    print("%d: %f" % (i, tc08usb[i]))
                
        self.dll = ctypes.windll.LoadLibrary('usbtc08.dll')
            
        # Open Unit
        self.handle = self.dll.usb_tc08_open_unit()
        
        if self.handle == 0:
            raise IOError("No more TC08 units found")
        elif self.handle < 0:
            err = self.dll.usb_tc08_get_last_error(0)
            raise IOError("USBTC08_ERROR {} {}".format(err, USBTC08_ERROR(err)))
        
        # Set mains filtering
        self.parse_err(
            self.dll.usb_tc08_set_mains(self.handle,1)) # 0: 50Hz 1: 60Hz

        # create C buffers for polling
        self.buffer_len = 1024
        self.times_buffer = np.zeros( self.buffer_len, dtype=np.int32) 
        self.temps_buffer  = np.zeros( self.buffer_len, dtype=np.float32)
        self.overflow = ctypes.c_int16()
        
        # create history buffers
        # history buffers have most recent reading at index 0
        self.hist_len = 1024*5
        self.times_history = np.zeros( (9, self.hist_len), dtype=np.int32)
        self.temps_history = np.zeros( (9, self.hist_len), dtype=np.float32)


        # set up channels
        for i, chan_name in enumerate(self.chan_names):
            if chan_name == "_":
                continue
            print("connecting channel",i)
            self.dll.usb_tc08_set_channel(self.handle, i, ord(b'K'))
            
        #self.dll.usb_tc08_run(self.handle, 1000)

        min_interval_ms = self.parse_err(
            self.dll.usb_tc08_get_minimum_interval_ms(self.handle))
        self.dll.usb_tc08_run(self.handle, min_interval_ms)

        # Background polling thread
        self.update_thread_interrupted = False
        self.update_thread = threading.Thread(target=self.update_thread_run)
        self.update_thread.start()

    def disconnect(self):
        
        self.settings.disconnect_all_from_hardware()

        
        if hasattr(self, 'update_thread'):
            self.update_thread_interrupted = True
            self.update_thread.join(timeout=1.0)
            del self.update_thread
        
        if hasattr(self, 'handle'):
            self.dll.usb_tc08_stop(self.handle)
            self.dll.usb_tc08_close_unit(self.handle)

        

        

    def parse_err(self, resp):
        if resp != 0: 
            return resp
        
        err = self.dll.usb_tc08_get_last_error(self.handle)
        raise IOError("USBTC08_ERROR {} {}".format(err, USBTC08_ERROR(err)))
            
    def update_thread_run(self):
        while not self.update_thread_interrupted:
            time.sleep(self.settings['update_time'])
            for i, chan_name in enumerate(self.chan_names):
                if chan_name == '_':
                    continue
                
                
                reads_transfered = self.dll.usb_tc08_get_temp(
                    self.handle,
                    self.temps_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    self.times_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                    self.buffer_len,
                    ctypes.byref(self.overflow),
                    i, #channel num
                    0, # degrees Celcius (1=F, 2=K, 3=R)
                    0, # fill in missing
                    )
                print("reading channel", i, "readings transfered", reads_transfered)

                if reads_transfered < 0:
                    print(reads_transfered)
                    err = self.dll.usb_tc08_get_last_error(self.handle)
                    raise IOError("USBTC08_ERROR {} {}".format(err, USBTC08_ERROR(err)))
                
                elif reads_transfered > 0:
                    np_ring_buffer_roll(self.times_history[i,:], 
                                        self.times_buffer[0:reads_transfered][::-1])
                    np_ring_buffer_roll(self.temps_history[i,:], 
                                        self.temps_buffer[0:reads_transfered][::-1])
                
                    self.settings[chan_name] = self.temps_history[i,0] # latest measurement
                        
        self.dll.usb_tc08_stop(self.handle)

            
            
            
def np_ring_buffer_roll(A, B):
    """Take a ring buffer numpy array A
    and place B at beginning, pushing off
    then end of A
    
    in-place update of A
    
    len(A) > len(B)
    
    example:
    A = np.array( [5,4,3,2,1] )
    B = np.array( [70,60] )
    np_ring_buffer_roll(A,B) 
    
    A == [70,60,5,4,3]
    """
    A[len(B):] = A[:len(A)-len(B)]
    A[:len(B)] = B
    return A
                
###

###
            
class USBTC08_ERROR(Enum):
    OK = 0
    OS_NOT_SUPPORTED = 1
    NO_CHANNELS_SET = 2
    INVALID_PARAMETER = 3
    VARIANT_NOT_SUPPORTED = 4
    INCORRECT_MODE = 5
    ENUMERATION_INCOMPLETE = 6
    NOT_RESPONDING = 7
    FW_FAIL = 8
    CONFIG_FAIL = 9
    NOT_FOUND = 10
    THREAD_FAIL = 11
    PIPE_INFO_FAIL = 12
    NOT_CALIBRATED = 13
    PICOPP_TOO_OLD = 14
    COMMUNICATION = 15
    INVALID_HANDLE = -1