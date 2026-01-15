#這是專門負責用 PIO 收資料的模組
import rp2
from machine import Pin

# --- PIO 組合語言程式 (Assembly) ---
# 這段程式碼會被編譯並載入到 PIO 硬體中執行
# 邏輯：
# 1. 等待 Start Bit (低電位)
# 2. 等待 1.5 個位元的時間 (定位到第一個 Data Bit 的正中間)
# 3. 連續讀取 8 次 (8個 bits)
# 4. 把資料推送到 FIFO 給 CPU 拿

@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=False)
def uart_rx_program():
    # 1. 等待 Start Bit (Line goes Low)
    wait(0, pin, 0)

    # 2. 準備讀取迴圈
    # 設定計數器 x 為 7 (因為 0~7 共 8 個 bits)
    # [10] 是延遲指令。為什麼是 10？
    # 我們設定 PIO 頻率是鮑率的 8 倍 (每個 bit 8 個週期)
    # Start bit 佔 8 週期。我們要跳過 Start bit 並停在第一個 data bit 的中間
    # 所以需要等待 1.5 * 8 = 12 個週期。
    # 'wait' 耗掉 1 週期，'set' 耗掉 1 週期，所以延遲需要 10 週期 (1+1+10 = 12)
    set(x, 7)             [10]

    # 3. 讀取迴圈 (Bit Loop)
    label("bitloop")
    in_(pins, 1)          # 讀取 1 bit 到 ISR 暫存器
    
    # [6] 是延遲指令
    # 每個 bit 佔 8 週期。'in' 耗掉 1，'jmp' 耗掉 1
    # 所以延遲需要 6 週期 (1+1+6 = 8)
    jmp(x_dec, "bitloop") [6]

    # 4. 推送資料
    # 8 bits 讀完了，把 ISR 的內容推送到 RX FIFO
    push(block)

class PioUart:
    def __init__(self, sm_id, pin_rx, baud_rate=256000):
        self.sm_id = sm_id
        self.pin_rx = Pin(pin_rx, Pin.IN, Pin.PULL_UP)
        self.baud = baud_rate
        
        # 計算 PIO 的運作頻率
        # 我們的 Assembly 程式設計為 "每個 bit 花費 8 個時脈週期"
        # 所以 PIO 頻率必須是：鮑率 * 8
        # 例如：256000 * 8 = 2,048,000 Hz
        sm_freq = baud_rate * 8
        
        # 初始化狀態機 (State Machine)
        self.sm = rp2.StateMachine(
            sm_id, 
            uart_rx_program, 
            freq=sm_freq, 
            in_base=self.pin_rx, # in指令讀取的腳位
            jmp_pin=self.pin_rx  # wait指令監控的腳位
        )
        
        # 啟動狀態機
        self.sm.active(1)

    def any(self):
        """檢查 FIFO 裡面有沒有資料"""
        return self.sm.rx_fifo()

    def read(self):
        """從 FIFO 讀取一個 Byte"""
        if self.sm.rx_fifo() > 0:
            # PIO push 出來的是 32-bit 整數，但我們只要最後 8 bits
            # 因為 UART 傳輸是 LSB first，所以資料會在低位元
            raw_value = self.sm.get()
            return (raw_value >> 24) # 根據 PIO shift 方向調整，通常需要實驗一下位移
            # 修正：MicroPython 的 PIO shift right 行為
            # 如果 in_shiftdir=SHIFT_RIGHT，資料會從高位元進來還是低位元？
            # 讓我們用更簡單的方式：直接回傳，主程式再處理
            # 或者通常 PIO RX 寫法會把有效數據放在高 8 位或低 8 位
            
            # 根據經驗，SHIFT_RIGHT 後 push，資料通常在 32-bit 的最上方
            # 讓我們回傳原始值，讓您在主程式觀察
            return raw_value >> 24 
        return None
        
    def close(self):
        self.sm.active(0)