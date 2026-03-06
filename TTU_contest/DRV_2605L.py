import machine
import time

# 初始化 I2C (Pico 2: GP4=SDA, GP5=SCL)
i2c = machine.I2C(0, sda=machine.Pin(4), scl=machine.Pin(5))
ADDR = 0x5a

def init_drv2605():
    # 退出待機模式
    i2c.writeto_mem(ADDR, 0x01, b'\x00')
    # 選擇內建效果庫 (1 代表 ERM 轉子馬達庫，最常用)
    i2c.writeto_mem(ADDR, 0x03, b'\x01')

def play_effect(effect_id):
    # 設定效果編號 (0x04 暫存器)
    i2c.writeto_mem(ADDR, 0x04, bytes([effect_id]))
    # 確保序列結束 (0x05 暫存器設為 0)
    i2c.writeto_mem(ADDR, 0x05, b'\x00')
    # 啟動播放 (0x0C 暫存器設為 1)
    i2c.writeto_mem(ADDR, 0x0C, b'\x01')

# 執行初始化
init_drv2605()

print("開始 1-123 效果輪播測試！")
print("------------------------")

try:
    for i in range(1, 124):
        print(f"正在播放效果編號: {i}")
        play_effect(i)
        
        # 每個效果之間停頓一下，讓你感受差異
        # 某些效果很短(點擊)，某些很長(嗡嗡聲)
        time.sleep(1.5) 
        
except KeyboardInterrupt:
    print("\n使用者停止測試")

print("輪播結束！")

