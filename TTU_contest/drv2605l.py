from machine import Pin, I2C

class DRV2605L:
    def __init__(self, i2c_bus=1, sda=14, scl=15):
        self.i2c = I2C(i2c_bus, sda=Pin(sda), scl=Pin(scl), freq=400000)
        self.addr = 0x5A
        self.active = False
        try:
            self.i2c.writeto_mem(self.addr, 0x01, b'\x00') 
            self.i2c.writeto_mem(self.addr, 0x03, b'\x01') 
            self.active = True
        except: pass

    def play_sequence(self, effects):
        if not self.active: return
        try:
            for i, eff in enumerate(effects):
                self.i2c.writeto_mem(self.addr, 0x04 + i, bytes([eff]))
            self.i2c.writeto_mem(self.addr, 0x0C, b'\x01')
        except: pass