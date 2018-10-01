from ScopeFoundry.base_app import BaseMicroscopeApp
from ScopeFoundryHW.pico_tc08 import pico_tc08_hw

class TC08_TestApp(BaseMicroscopeApp):
    
    name = 'tc08_test_app'
    
    def setup(self):
        
        self.add_hardware(pico_tc08_hw.PicoTC08_HW(self, 
            chan_names="012_____8"))
        

if __name__ == '__main__':
    
    app = TC08_TestApp()
    
    app.exec_()