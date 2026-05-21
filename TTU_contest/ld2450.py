import rp2
from machine import Pin
import struct
import math

# PIO UART 接收暫存器定義
@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, fifo_join=rp2.PIO.JOIN_RX, autopush=True, push_thresh=32)
def pio_uart_rx():
    label("start")
    wait(0, pin, 0)
    set(x, 7) [10]
    label("bitloop")
    in_(pins, 1)
    jmp(x_dec, "bitloop") [6]
    wait(1, pin, 0)
    jmp("start")

class LD2450_PIO:
    def __init__(self, sm_id=0, pin_rx=1, baud=460800):
        self.raw_data = bytearray()
        self.pin_rx = Pin(pin_rx, Pin.IN, Pin.PULL_UP)
        self.sm = rp2.StateMachine(sm_id, pio_uart_rx, freq=8 * baud, in_base=self.pin_rx)
        self.sm.active(1)
        self.HEADER = b'\xAA\xFF\x03\x00'

    def parse(self, pitch=0, roll=0):
        while self.sm.rx_fifo():
            self.raw_data.extend(struct.pack('<I', self.sm.get()))
        if len(self.raw_data) > 256: self.raw_data = self.raw_data[-128:]
        
        head = self.raw_data.rfind(self.HEADER)
        if head == -1 or len(self.raw_data) - head < 30: return None
        
        packet = self.raw_data[head : head + 30]
        self.raw_data = self.raw_data[head + 30:]
        if packet[28:30] != b'\x55\xCC': return None
        
        targets = []
        cp, sp = math.cos(pitch), math.sin(pitch)
        cr, sr = math.cos(roll), math.sin(roll)
        
        for i in range(3):
            off = 4 + (i * 8)
            x_raw, y_raw = struct.unpack('<hh', packet[off:off+4])
            xr = -(x_raw & 0x7FFF) if x_raw & 0x8000 else (x_raw & 0x7FFF)
            yr = -(y_raw & 0x7FFF) if y_raw & 0x8000 else (y_raw & 0x7FFF)
            if xr != 0 or yr != 0:
                yf = yr * cp
                xf = xr * cr - (yr * sp) * sr
                targets.append((xf, yf))
        return targets