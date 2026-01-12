
from machine import UART, Pin
import time
import struct

# 初始化 UART
# ID=0, Baudrate=256000 (文件指定規格), TX=GP0, RX=GP1
uart = UART(0, baudrate=256000, tx=Pin(0), rx=Pin(1))

print("LD2450 Radar Test Started...")
print("Waiting for data stream...")

buffer = b''

while True:
    if uart.any():
        # 讀取數據並存入緩衝區
        chunk = uart.read()
        if chunk:
            buffer += chunk
        
        # 尋找幀頭: AA FF 03 00 (LD2450 基礎追蹤模式)
        header_index = buffer.find(b'\xAA\xFF\x03\x00')
        
        if header_index != -1:
            # 確保緩衝區有足夠長的數據來解析 (至少一個目標的長度)
            # 標頭(4) + 目標1資訊(8) + ... 
            # 這裡我們只讀取第一個目標做測試，需要至少 12 bytes
            if len(buffer) >= header_index + 12:
                # 提取目標數據 (跳過標頭 4 bytes)
                payload = buffer[header_index + 4 : header_index + 12]
                
                # 使用 struct 解析二進位資料 (Little Endian <)
                # h: 2 bytes signed short (X 座標)
                # h: 2 bytes signed short (Y 座標)
                # h: 2 bytes signed short (速度)
                # H: 2 bytes unsigned short (距離解析度)
                try:
                    target_x, target_y, speed, resolution = struct.unpack('<hhhH', payload)
                    
                    # 修正數值顯示 (有些版本 X 最高位代表負號，但 struct signed short 通常已處理)
                    print(f"Target -> X: {target_x}mm, Y: {target_y}mm, Speed: {speed}cm/s")
                    
                except Exception as e:
                    print("Parse Error:", e)
                
                # 移除已處理的數據，保持緩衝區乾淨
                buffer = buffer[header_index + 12:]
                
    # 簡單的緩衝區清理機制，避免記憶體溢出
    if len(buffer) > 200:
        buffer = b''
        
    time.sleep(0.005) # 極短暫休眠，讓出 CPU 資源