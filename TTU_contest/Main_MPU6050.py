import machine
import time
import MPU6050

# 1. 設定 I2C 介面
# 提醒：請確認你的 SDA 接在 GP14，SCL 接在 GP15
# freq=100000 (100kHz) 是 MPU6050 最穩定的通訊頻率
i2c = machine.I2C(1, sda=machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP), 
                     scl=machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP), 
                     freq=100000)

# 2. 初始化 MPU6050 類別
mpu = MPU6050.MPU6050(i2c)

# 3. 將 MPU6050 從休眠模式中喚醒
mpu.wake()

print("MPU6050 初始化成功，開始讀取數據...")

# 4. 持續列印數據
while True:
    try:
        # 讀取陀螺儀數據
        gyro = mpu.read_gyro_data()
        # 讀取加速度數據
        accel = mpu.read_accel_data()
        
        # 格式化輸出，讓數據更容易閱讀
        print("陀螺儀 (Gyro): X:{:>7.2f} Y:{:>7.2f} Z:{:>7.2f} | 加速度 (Accel): X:{:>5.2f} Y:{:>5.2f} Z:{:>5.2f}".format(
            gyro[0], gyro[1], gyro[2], accel[0], accel[1], accel[2]
        ))
        
    except OSError as e:
        # 如果發生通訊錯誤 (EIO)，嘗試重新喚醒或跳過
        print("通訊錯誤 (EIO):", e)
        
    time.sleep(0.1)
