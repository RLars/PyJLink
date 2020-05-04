import pylink
from cmsis_svd.parser import SVDParser
import cmsis_svd.data

import functools

class JLink(pylink.JLink):
    # Store device rather than svd object, as parsing to device takes much time. So store this in ram.
    svd_device = None

    def __init__(self, device_name):
        pylink.JLink.__init__(self)
        if self.num_connected_emulators() == 0:
            print ('No emulator connected. Leaving...')
            exit()
        elif self.num_connected_emulators() == 1:
            self.open()
        else:
            print ('List of available emulators:')
            print(self.connected_emulators())
            print ('Enter serial number of emulator which shall be connected:')
            snum = input()
            self.open(snum)
        
        svd = SVDParser.for_mcu(device_name)
        if svd is None:
            print('SVD parser input parameters could not be determined')
            exit()

        self.svd_device = svd.get_device()
        
        self.connect(device_name, verbose=True)

    @functools.lru_cache(maxsize=128)
    def get_reg_address(self, peripheral_name, register_name):
        addr = None
        if not self.svd_device is None:
            p = next((x for x in self.svd_device.peripherals if x.name == peripheral_name), None)
            if not p is None:
                r = next((x for x in p.registers if x.name == register_name), None)
                if not r is None:
                    addr = p.base_address + r.address_offset
        return addr

    def modify_register(self, peripheral_name, register_name, bitmask, value):
        reg_addr = self.get_reg_address(peripheral_name, register_name)
        if not reg_addr is None:
            self.memory_write32(reg_addr, [self.memory_read32(reg_addr, 1)[0] & (~ bitmask) | value])

    def read_register(self, peripheral_name, register_name):
        reg_addr = self.get_reg_address(peripheral_name, register_name)
        if not reg_addr is None:
            return self.memory_read32(reg_addr, 1)[0]

    def gpio_setmode(self, peripheral_name, pin_num, mode):
        self.modify_register(peripheral_name, 'MODER', (0b11 << pin_num*2), (mode << pin_num*2))

    def gpio_setoutput(self, peripheral_name, pin_num, output):
        self.modify_register(peripheral_name, 'ODR', (0b1 << pin_num), (output << pin_num))
    
    def gpio_getinput(self, peripheral_name, pin_num):
        return (self.read_register(peripheral_name, 'IDR') >> pin_num) & 1