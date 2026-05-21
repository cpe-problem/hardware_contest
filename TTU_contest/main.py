from machine import Timer, idle
import time
import math
import _thread
import gc

# 引入自訂模組
from ld2450 import LD2450_PIO
from drv2605l import DRV2605L
from mpu6050 import MPU6050

# --- 全域共享變數 ---
pending_seq = [8, 178, 8, 178, 8, 178, 0, 0] 
lock = _thread.allocate_lock()
haptic_busy = False
new_data_available = False
temp_min_dists = [800.0, 800.0, 800.0]

# --- Core 1: 觸覺回饋執行緒 ---
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

    tim_haptic_poll.init(period=20, mode=Timer.PERIODIC, callback=haptic_poll_callback)
    
    while True:
        idle()

# 啟動第二核心
_thread.stack_size(4096)
_thread.start_new_thread(core1_task, ())

# --- Core 0: 主邏輯與判定 ---
radar = LD2450_PIO(sm_id=0, pin_rx=1)
imu = MPU6050(i2c_bus=0, sda=4, scl=5)

def logic_timer_callback(t):
    global new_data_available
    p, r = imu.get_fusion_data()
    targets = radar.parse(pitch=p, roll=r)
    
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

# --- 記憶體回收定時器 ---
def gc_timer_callback(t):
    gc.collect()

Timer(-1).init(period=2000, mode=Timer.PERIODIC, callback=gc_timer_callback)

print("系統啟動：全模組化事件驅動架構")

while True:
    idle()