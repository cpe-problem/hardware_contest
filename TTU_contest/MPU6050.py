import machine
import time

class MPU6050:
    """用於透過 I2C 從 MPU-6050 模組讀取陀螺儀速率和加速度數據的類別。"""

    def __init__(self, i2c: machine.I2C, address: int = 0x68):
        """
        創建一個新的 MPU6050 類別。
        :param i2c: 已設定好的 machine 模組 I2C 物件。
        :param address: MPU-6050 的 I2C 地址（預設為 0x68）。
        """
        self.address = address
        self.i2c = i2c

    def wake(self) -> None:
        """喚醒 MPU-6050。"""
        self.i2c.writeto_mem(self.address, 0x6B, bytes([0x01]))

    def sleep(self) -> None:
        """
        讓 MPU-6050 進入休眠模式（低功耗）。
        這會停止內部新數據的讀取。
        """
        self.i2c.writeto_mem(self.address, 0x6B, bytes([0x40]))

    def who_am_i(self) -> int:
        """返回 MPU-6050 的地址（用於確保通訊正常）。"""
        return self.i2c.readfrom_mem(self.address, 0x75, 1)[0]

    def read_temperature(self) -> float:
        """讀取 MPU-6050 內置溫度感測器的攝氏溫度。"""
        data = self.i2c.readfrom_mem(self.address, 0x41, 2)
        raw_temp: float = self._translate_pair(data[0], data[1])
        temp: float = (raw_temp / 340.0) + 36.53
        return temp

    def read_gyro_range(self) -> int:
        """讀取陀螺儀量程設定。"""
        return self._hex_to_index(self.i2c.readfrom_mem(self.address, 0x1B, 1)[0])

    def write_gyro_range(self, range_idx: int) -> None:
        """設置陀螺儀量程。"""
        self.i2c.writeto_mem(self.address, 0x1B, bytes([self._index_to_hex(range_idx)]))

    def read_gyro_data(self) -> tuple[float, float, float]:
        """讀取陀螺儀數據，回傳 (x, y, z) 元組。"""
        gr: int = self.read_gyro_range()
        modifier: float = 131.0
        if gr == 1:
            modifier = 65.5
        elif gr == 2:
            modifier = 32.8
        elif gr == 3:
            modifier = 16.4

        # 讀取 6 位元組的陀螺儀數據
        data = self.i2c.readfrom_mem(self.address, 0x43, 6)
        x: float = (self._translate_pair(data[0], data[1])) / modifier
        y: float = (self._translate_pair(data[2], data[3])) / modifier
        z: float = (self._translate_pair(data[4], data[5])) / modifier
        return (x, y, z)

    def read_accel_range(self) -> int:
        """讀取加速度計量程設定。"""
        return self._hex_to_index(self.i2c.readfrom_mem(self.address, 0x1C, 1)[0])

    def write_accel_range(self, range_idx: int) -> None:
        """設置加速度計量程。"""
        self.i2c.writeto_mem(self.address, 0x1C, bytes([self._index_to_hex(range_idx)]))

    def read_accel_data(self) -> tuple[float, float, float]:
        """讀取加速度數據，回傳 (x, y, z) 元組。"""
        ar: int = self.read_accel_range()
        modifier: float = 16384.0
        if ar == 1:
            modifier = 8192.0
        elif ar == 2:
            modifier = 4096.0
        elif ar == 3:
            modifier = 2048.0

        # 讀取 6 位元組的加速度數據
        data = self.i2c.readfrom_mem(self.address, 0x3B, 6)
        x: float = (self._translate_pair(data[0], data[1])) / modifier
        y: float = (self._translate_pair(data[2], data[3])) / modifier
        z: float = (self._translate_pair(data[4], data[5])) / modifier
        return (x, y, z)

    def read_lpf_range(self) -> int:
        """讀取低通濾波器設定。"""
        return self.i2c.readfrom_mem(self.address, 0x1A, 1)[0]

    def write_lpf_range(self, lpf_range: int) -> None:
        """
        設置低通濾波器範圍。
        :param lpf_range: 0-6。0 = 最小過濾，6 = 最大過濾。
        """
        if lpf_range < 0 or lpf_range > 6:
            raise Exception("無效的低通濾波器設定: " + str(lpf_range))
        self.i2c.writeto_mem(self.address, 0x1A, bytes([lpf_range]))

    #### 工具函數 ####

    def _translate_pair(self, high: int, low: int) -> int:
        """將位元組對轉換為可用值。"""
        value = (high << 8) + low
        if value >= 0x8000:
            value = -((65535 - value) + 1)
        return value

    def _hex_to_index(self, range_hex: int) -> int:
        """將十六進位量程設定轉換為整數索引 (0-3)。"""
        if range_hex == 0x00:
            return 0
        elif range_hex == 0x08:
            return 1
        elif range_hex == 0x10:
            return 2
        elif range_hex == 0x18:
            return 3
        else:
            raise Exception("找到未知的量程設定: " + str(range_hex))

    def _index_to_hex(self, index: int) -> int:
        """將索引 (0-3) 轉換為十六進位量程設定。"""
        if index == 0:
            return 0x00
        elif index == 1:
            return 0x08
        elif index == 2:
            return 0x10
        elif index == 3:
            return 0x18
        else:
            raise Exception("無效的量程索引: " + str(index) + "。必須為 0-3。")
