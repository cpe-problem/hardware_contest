from machine import Pin, I2C
import time
import struct

# --- 設定 I2C ---
# 使用 I2C0, SDA=GP0, SCL=GP1
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)

# MPU6050 的預設位址
MPU_ADDR = 0x68

def init_mpu6050():
    try:
        # 掃描 I2C 設備
        devices = i2c.scan()
        if MPU_ADDR not in devices:
            print(f"❌ 找不到 MPU6050 (位址 0x{MPU_ADDR:X})")
            print(f"   目前掃描到的設備: {[hex(d) for d in devices]}")
            return False
            
        # 喚醒 MPU6050 (寫入 0 到電源管理暫存器 0x6B)
        i2c.writeto_mem(MPU_ADDR, 0x6B, b'\x00')
        time.sleep(0.1)
        print("✅ MPU6050 初始化成功！")
        return True
    except Exception as e:
        print(f"❌ 初始化發生錯誤: {e}")
        return False

def get_data():
    try:
        # 從暫存器 0x3B 開始，一次讀取 14 個 bytes
        # 包含：加速度(6) + 溫度(2) + 角速度(6)
        data = i2c.readfrom_mem(MPU_ADDR, 0x3B, 14)
        
        # 解析二進位資料 (>hhhhhhh 代表 7 個 Big-endian Short整數)
        values = struct.unpack(">hhhhhhh", data)
        
        # 拆解數據
        accel_x = values[0]
        accel_y = values[1]
        accel_z = values[2]
        temp    = values[3] / 340.00 + 36.53 # 溫度換算公式
        gyro_x  = values[4]
        gyro_y  = values[5]
        gyro_z  = values[6]
        
        return accel_x, accel_y, accel_z, temp, gyro_x, gyro_y, gyro_z
    except Exception as e:
        print(f"讀取錯誤: {e}")
        return None

# --- 主程式 ---
if init_mpu6050():
    print("\n開始讀取數據 (按 Ctrl+C 停止)...")
    print(f"{'Accel X':^8} | {'Accel Y':^8} | {'Accel Z':^8} | {'Temp':^6} | {'Gyro X':^8} | {'Gyro Y':^8} | {'Gyro Z':^8}")
    print("-" * 80)
    
    while True:
        data = get_data()
        if data:
            ax, ay, az, t, gx, gy, gz = data
            # 使用 \r 讓數值在同一行更新
            print(f"{ax:8d} | {ay:8d} | {az:8d} | {t:6.1f} | {gx:8d} | {gy:8d} | {gz:8d}", end='\r')
        
        time.sleep(0.1) # 更新頻率