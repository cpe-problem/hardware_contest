
from machine import I2C, Pin
import time

# DRV2605 暫存器地址
DRV2605_ADDR = 0x5A
REG_MODE = 0x01
REG_RTPIN = 0x02
REG_LIBRARY = 0x03
REG_WAVESEQ1 = 0x04
REG_WAVESEQ2 = 0x05
REG_GO = 0x0C
REG_FEEDBACK = 0x1A

# 初始化 I2C
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)

def write_reg(reg, val):
    i2c.writeto_mem(DRV2605_ADDR, reg, bytes([val]))

def init_drv2605_lra():
    # 掃描 I2C 確認裝置存在
    devices = i2c.scan()
    if DRV2605_ADDR not in devices:
        print("Error: DRV2605 not found!")
        return False

    print("DRV2605 found. Initializing for LRA...")
    
    # 1. 進入待機模式以修改設定
    write_reg(REG_MODE, 0x00) 
    
    # 2. 【關鍵】設定回授暫存器以支援 LRA 馬達
    # 預設是 0x36 (ERM)，LRA 必須將 Bit 7 設為 1
    # 這裡寫入 0xB6 (LRA Mode, 4x Braking, Medium Loop Gain)
    write_reg(REG_FEEDBACK, 0xB6)
    
    # 3. 選擇 LRA 專用的波形庫 (Library 6)
    write_reg(REG_LIBRARY, 0x06)
    
    # 4. 啟用晶片 (非待機)
    write_reg(REG_MODE, 0x00)
    
    return True

def play_effect(effect_id):
    # 設定波形序列
    write_reg(REG_WAVESEQ1, effect_id) # 第一個動作
    write_reg(REG_WAVESEQ2, 0x00)      # 結束序列
    
    # 發射 (GO bit)
    write_reg(REG_GO, 0x01)

# --- 主程式 ---
if init_drv2605_lra():
    print("Initialization Complete.")
    
    while True:
        print("Effect 1: Strong Click")
        play_effect(1)
        time.sleep(1)
        
        print("Effect 12: Triple Click")
        play_effect(12)
        time.sleep(1)
        
        print("Effect 52: Pulsing Strong (Warning)")
        play_effect(52)
        time.sleep(2)