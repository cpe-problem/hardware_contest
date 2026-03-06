from machine import UART, Pin
import ustruct
import time

# 1. 初始化 UART (Pico 2W: GP0=TX, GP1=RX)
uart = UART(0, baudrate=256000, tx=Pin(0), rx=Pin(1))
led = Pin("LED", Pin.OUT)

def parse_ld2450():
    # 確保緩存中有足夠長度
    if uart.any() >= 30:
        # 尋找幀頭 0xAA FF 03 00，防止數據錯位
        if uart.read(1) == b'\xAA':
            header_rest = uart.read(3)
            if header_rest == b'\xFF\x03\x00':
                # 讀取後續的 26 Byte (目標數據 + 幀尾)
                data = uart.read(26)
                if len(data) < 26: return
                
                led.toggle() # 成功解析一次就閃燈
                print("-" * 30)
                
                # 解析 3 個目標
                for i in range(3):
                    offset = i * 8
                    t = data[offset : offset + 8]
                    
                    # 使用 <H (無符號短整數) 讀取原始 16 位元
                    raw_x = ustruct.unpack('<H', t[0:2])[0]
                    raw_y = ustruct.unpack('<H', t[2:4])[0]
                    # 速度通常直接用 <h (帶正負號) 即可
                    speed = ustruct.unpack('<h', t[4:6])[0]
                    
                    # --- 關鍵修正：處理 LD2450 的 15-bit 數值 + 1-bit 符號位 ---
                    # 如果最高位 (0x8000) 為 1，代表負值
                    x = (raw_x & 0x7FFF) * (-1 if raw_x & 0x8000 else 1)
                    y = (raw_y & 0x7FFF) * (-1 if raw_y & 0x8000 else 1)
                    
                    # 排除無效目標 (Y=0 代表沒偵測到)
                    # 註：如果 Y 仍為負，代表目標在雷達後方或為雜訊
                    if y != 0:
                        print(f"目標 {i+1}: X={x:5}mm, Y={y:5}mm, 速度={speed:3}cm/s")

# 主迴圈
print("LD2450 專業測試模式啟動 (已修正符號位解析)...")
while True:
    parse_ld2450()
    # 保持高速讀取，防止 UART 緩存堆積導致亂碼
    time.sleep_ms(10)

