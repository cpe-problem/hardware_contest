from machine import I2C, Pin
import ssd1306

class DisplayUnit:
    def __init__(self):
        self.i2c = I2C(1, scl=Pin(15), sda=Pin(14))
        self.oled = ssd1306.SSD1306_I2C(128, 64, self.i2c)

    def show_menu(self, title, names, cursor):
        self.oled.fill(0)

        # --- 可視窗顯示最大數量 ---
        window_size = 5   # 可調整，5 或 6 都可以
    
        # 計算視窗起始位置
        start = 0
        if cursor >= window_size:
            start = cursor - window_size + 1

        # 計算視窗結束
        end = min(start + window_size, len(names))

        # 顯示標題
        self.oled.text(title, 0, 0)

        # 顯示 window range 內的項目
        y = 12
        for idx in range(start, end):
            mark = ">" if idx == cursor else " "
            self.oled.text(mark + names[idx], 0, y)
            y += 10

        self.oled.show()


    def show_message(self, msg):
        self.oled.fill(0)
        self.oled.text(msg, 0, 30)
        self.oled.show()

