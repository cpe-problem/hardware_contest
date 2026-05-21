from machine import Pin, I2C
import time
import math
import struct

class MPU6050:
    def __init__(self, i2c_bus=0, sda=4, scl=5):
        self.i2c = I2C(i2c_bus, sda=Pin(sda), scl=Pin(scl), freq=400000)
        self.addr = 0x68
        self.pitch = self.roll = 0.0
        self.last_time = time.ticks_ms()
        try:
            self.i2c.writeto_mem(self.addr, 0x6B, b'\x00')
            self.active = True
        except: self.active = False

    def get_fusion_data(self):
        if not self.active: return 0.0, 0.0
        try:
            d = self.i2c.readfrom_mem(self.addr, 0x3B, 14)
            v = struct.unpack('>hhhhhhh', d)
            now = time.ticks_ms()
            dt = time.ticks_diff(now, self.last_time) / 1000.0
            self.last_time = now
            
            acc_p = math.atan2(v[1], math.sqrt(v[0]**2 + v[2]**2))
            acc_r = math.atan2(-v[0], v[2])
            gy_p, gy_r = (v[4]/131.0)*0.01745, (v[5]/131.0)*0.01745
            
            alpha = 0.96
            self.pitch = alpha * (self.pitch + gy_p * dt) + (1 - alpha) * acc_p
            self.roll = alpha * (self.roll + gy_r * dt) + (1 - alpha) * acc_r
            return self.pitch, self.roll
        except: return 0.0, 0.0