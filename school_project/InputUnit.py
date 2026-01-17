from machine import Pin, ADC
import time

class InputUnit:
    def __init__(self):
        # ------------------------------------------------
        # 硬體腳位設定
        # ------------------------------------------------
        
        # 1. 搖桿 X 軸 (VRX) -> 接 GP26
        # 用來負責：返回上一頁(往左)、調整數值(左右)
        self.joy_x = ADC(26)
        
        # 2. 搖桿 Y 軸 (VRY) -> 接 GP28
        # 用來負責：選單上下移動
        self.joy_y = ADC(28)
        
        # 3. 搖桿按鈕 (SW) -> 接 GP22
        # 用來負責：確認 / 進入 (Enter)
        # 搖桿按鈕通常是浮接的，一定要開 PULL_UP
        self.joy_sw = Pin(7, Pin.IN, Pin.PULL_UP)

    def read_joy_x(self):
        """ 讀取 X 軸數值 (0 ~ 65535) """
        return self.joy_x.read_u16()

    def read_joy_y(self):
        """ 讀取 Y 軸數值 (0 ~ 65535) """
        return self.joy_y.read_u16()

    def is_enter_pressed(self):
        """ 
        檢查搖桿按鈕是否被按下 
        因為有開上拉電阻，沒按是 1，按下是 0
        """
        if self.joy_sw.value() == 0:
            return True
        return False