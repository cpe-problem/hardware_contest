# mpu6050.py - 修正後的 Pico 專用驅動
from machine import I2C
from time import sleep_ms
import math

# --- 暫存器地址與常數 ---
_PWR_MGMT_1 = 0x6B
_ACCEL_XOUT0 = 0x3B
_TEMP_OUT0 = 0x41
_GYRO_XOUT0 = 0x43
_ACCEL_CONFIG = 0x1C
_GYRO_CONFIG = 0x1B
_MPU6050_ADDRESS = 0x68

# 輔助函式：處理有號整數
def signedIntFromBytes(x, endian="big"):
    y = int.from_bytes(x, endian)
    if (y >= 0x8000):
        return -((65535 - y) + 1)
    else:
        return y

class MPU6050():
    def __init__(self, i2c, addr=_MPU6050_ADDRESS):
        """
        初始化 MPU6050
        :param i2c: 已經設定好的 machine.I2C 物件
        :param addr: I2C 地址 (預設 0x68)
        """
        self.i2c = i2c
        self.addr = addr
        
        # 喚醒 MPU6050 (解除休眠模式)
        try:
            self.i2c.writeto_mem(self.addr, _PWR_MGMT_1, bytes([0x00]))
            sleep_ms(5)
        except OSError:
            print("錯誤: 找不到 MPU6050，請檢查接線！")

        # 預設設定範圍
        self._accel_range = 0
        self._gyro_range = 0
        self.set_accel_range(0x00) # 2G
        self.set_gyro_range(0x00)  # 250 deg/s

    # --- 讀寫底層 ---
    def _readData(self, register):
        data = self.i2c.readfrom_mem(self.addr, register, 6)
        x = signedIntFromBytes(data[0:2])
        y = signedIntFromBytes(data[2:4])
        z = signedIntFromBytes(data[4:6])
        return {"x": x, "y": y, "z": z}

    # --- 加速度計 (Accelerometer) ---
    def set_accel_range(self, accel_range):
        self.i2c.writeto_mem(self.addr, _ACCEL_CONFIG, bytes([accel_range]))
        self._accel_range = accel_range

    def read_accel_data(self, g=False):
        raw_data = self._readData(_ACCEL_XOUT0)
        
        # 設定比例尺
        scale = 16384.0 # 預設 2G
        if self._accel_range == 0x08: scale = 8192.0
        elif self._accel_range == 0x10: scale = 4096.0
        elif self._accel_range == 0x18: scale = 2048.0

        x = raw_data["x"] / scale
        y = raw_data["y"] / scale
        z = raw_data["z"] / scale

        if g: return {"x": x, "y": y, "z": z}
        else: return {"x": x * 9.80665, "y": y * 9.80665, "z": z * 9.80665}

    # --- 陀螺儀 (Gyroscope) ---
    def set_gyro_range(self, gyro_range):
        self.i2c.writeto_mem(self.addr, _GYRO_CONFIG, bytes([gyro_range]))
        self._gyro_range = gyro_range

    def read_gyro_data(self):
        raw_data = self._readData(_GYRO_XOUT0)
        
        scale = 131.0 # 預設 250 deg/s
        if self._gyro_range == 0x08: scale = 65.5
        elif self._gyro_range == 0x10: scale = 32.8
        elif self._gyro_range == 0x18: scale = 16.4

        return {
            "x": raw_data["x"] / scale,
            "y": raw_data["y"] / scale,
            "z": raw_data["z"] / scale
        }

    # --- 溫度 ---
    def read_temperature(self):
        data = self.i2c.readfrom_mem(self.addr, _TEMP_OUT0, 2)
        raw_temp = signedIntFromBytes(data)
        return (raw_temp / 340.0) + 36.53