from machine import Pin, Timer, I2C, idle
import time
import math
import struct
import _thread
import rp2
import gc

# --- 1. PIO UART 接收 (LD2450 資料流) ---
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

# --- 2. 硬體類別定義 ---
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

# --- 3. 全域共享變數 ---
pending_seq = [8, 178, 8, 178, 8, 178, 0, 0] 
lock = _thread.allocate_lock()
haptic_busy = False
new_data_available = False
temp_min_dists = [800.0, 800.0, 800.0]

# --- 4. Core 1: 完全 Timer 驅動的執行緒 ---
def core1_task():
    global haptic_busy, new_data_available
    drv = DRV2605L(i2c_bus=1, sda=14, scl=15)
    tim_haptic_poll = Timer(-1)
    tim_cooldown = Timer(-1)

    def unlock_haptic(t):
        global haptic_busy
        haptic_busy = False

    def haptic_poll_callback(t):
        global haptic_busy, new_data_available
        if not haptic_busy and new_data_available:
            with lock:
                drv.play_sequence(pending_seq)
                new_data_available = False
            haptic_busy = True
            tim_cooldown.init(period=1800, mode=Timer.ONE_SHOT, callback=unlock_haptic)

    # 檢查間隔調短，讓反應更敏銳
    tim_haptic_poll.init(period=20, mode=Timer.PERIODIC, callback=haptic_poll_callback)
    
    while True:
        # 移除任何 sleep，使用 machine.idle() 讓執行緒處於低負載存活狀態
        idle()

_thread.stack_size(4096)
_thread.start_new_thread(core1_task, ())

# --- 5. Core 0: 邏輯與判定 ---
radar = LD2450_PIO(sm_id=0, pin_rx=1)
imu = MPU6050(i2c_bus=0, sda=4, scl=5)

def logic_timer_callback(t):
    global new_data_available
    p, r = imu.get_fusion_data()
    targets = radar.parse(pitch=p, roll=r)
    
    # 重置最近距離
    for i in range(3): temp_min_dists[i] = 800.0

    if targets:
        for tx, ty in targets:
            dist = math.sqrt(tx*tx + ty*ty) / 10.0
            angle = math.degrees(math.atan2(tx, ty))
            angle1 = 180 - angle

            idx = 1 # 中
            if 15 < angle1 <= 165:      idx = 0 # 左
            elif 195 <= angle1 < 345:   idx = 2 # 右
            
            if dist < temp_min_dists[idx]:
                temp_min_dists[idx] = dist

        with lock:
            for i in range(3):
                d = temp_min_dists[i]
                if d < 300:    code = 16
                elif d < 600:  code = 47
                else:          code = 8
                pending_seq[i * 2] = code
            new_data_available = True

tim_logic = Timer(-1)
tim_logic.init(period=100, mode=Timer.PERIODIC, callback=logic_timer_callback)

# --- 6. 記憶體回收定時器 ---
def gc_timer_callback(t):
    gc.collect()

# 每 2 秒強制清理一次記憶體
Timer(-1).init(period=2000, mode=Timer.PERIODIC, callback=gc_timer_callback)

print("系統啟動：全 Timer 事件驅動架構 (無 Sleep 阻塞)")

# 主迴圈只負責維持運行，不再有時間暫停
while True:
    idle()
