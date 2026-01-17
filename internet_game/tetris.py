from machine import Pin, PWM, I2C, ADC
import time, random
import ssd1306

# ==============================================
# 硬體驅動層
# ==============================================
class DisplayUnit:
    def __init__(self):
        self.i2c = I2C(0, sda=Pin(14), scl=Pin(15), freq=400000)
        self.oled = ssd1306.SSD1306_I2C(128, 64, self.i2c)

class InputUnit:
    def __init__(self):
        self.joy_x = ADC(Pin(26))
        self.joy_y = ADC(Pin(27))
        self.btn = Pin(16, Pin.IN, Pin.PULL_UP)
        self.last_btn_state = 1

    def read_axis(self):
        # 回傳: 0(無), -1(左/上), 1(右/下)
        x_val, y_val = self.joy_x.read_u16(), self.joy_y.read_u16()
        dx, dy = 0, 0
        if x_val < 15000: dx = -1
        elif x_val > 50000: dx = 1
        
        if y_val < 15000: dy = -1 # 視安裝方向調整，假設 <15000 是上(旋轉)
        elif y_val > 50000: dy = 1
        return dx, dy

    def check_btn_press(self):
        # 偵測按鈕剛被按下的瞬間 (Rising Edge)
        curr = self.btn.value()
        is_pressed = False
        if curr == 0 and self.last_btn_state == 1:
            is_pressed = True
        self.last_btn_state = curr
        return is_pressed

# ==============================================
# 遊戲常數與形狀
# ==============================================
BLOCK_SIZE = 4
FIELD_W, FIELD_H = 10, 16
OFFSET_X, OFFSET_Y = 34, 0  # 將遊戲區移到中間，左邊放 Hold，右邊放 Next

# 定義形狀與其 ID (用於顏色或邏輯區分)
# 格式: [形狀矩陣, ID]
SHAPES_DEF = [
    ([[1, 1, 1, 1]], 1),             # I
    ([[1, 1], [1, 1]], 2),           # O
    ([[0, 1, 0], [1, 1, 1]], 3),     # T
    ([[1, 0, 0], [1, 1, 1]], 4),     # L
    ([[0, 0, 1], [1, 1, 1]], 5),     # J
    ([[0, 1, 1], [1, 1, 0]], 6),     # S
    ([[1, 1, 0], [0, 1, 1]], 7)      # Z
]

# SRS Wall Kick 測試偏移量 (標準 SRS 很複雜，這裡用簡化版：左右、上、上左、上右)
# 順序：原點 -> 左 -> 右 -> 上(由地板踢起) -> 左上 -> 右上
KICK_OFFSETS = [(0,0), (-1,0), (1,0), (0,-1), (-1,-1), (1,-1)]

class TetrisGame:
    def __init__(self, display, inputs):
        self.disp = display
        self.oled = display.oled
        self.inputs = inputs
        self.buzzer = PWM(Pin(9))
        self.buzzer.duty_u16(0)
        
        self.reset_game()

    def reset_game(self):
        self.field = [[0] * FIELD_W for _ in range(FIELD_H)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        
        # 7-Bag 系統
        self.bag = []
        self.hold_shape = None
        self.hold_used = False  # 每個方塊只能 Hold 一次
        
        self.current_shape = None
        self.current_id = 0
        self.cx, self.cy = 0, 0
        
        self.next_shape_def = self.get_from_bag()
        self.spawn_piece()
        
        # 計時器
        self.fall_speed = 1000  # ms
        self.last_fall_time = time.ticks_ms()
        
        # 鎖定延遲 (Lock Delay)
        self.lock_delay = 500   # ms
        self.lock_timer = None  # None 表示沒接觸地面
        self.moves_reset_cnt = 0 # 限制在地板上移動重置計時器的次數 (防無限拖延)

    # --- 7-Bag 隨機生成 ---
    def get_from_bag(self):
        if not self.bag:
            self.bag = list(SHAPES_DEF) # 複製一份
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn_piece(self):
        self.current_shape = self.next_shape_def[0]
        self.current_id = self.next_shape_def[1]
        self.next_shape_def = self.get_from_bag()
        
        self.cx = FIELD_W // 2 - len(self.current_shape[0]) // 2
        self.cy = -len(self.current_shape) # 從畫面上方生成
        
        self.hold_used = False
        self.lock_timer = None
        self.moves_reset_cnt = 0

        # 檢查是否一出生就死
        if self.check_collision(self.current_shape, self.cx, self.cy):
            self.game_over = True

    # --- 核心邏輯 ---
    def check_collision(self, shape, ox, oy):
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    bx = ox + x
                    by = oy + y
                    if bx < 0 or bx >= FIELD_W or by >= FIELD_H:
                        return True
                    if by >= 0 and self.field[by][bx]:
                        return True
        return False

    def rotate_matrix(self, shape):
        return [list(row) for row in zip(*shape[::-1])]

    # SRS Wall Kick 嘗試
    def try_rotate(self):
        new_shape = self.rotate_matrix(self.current_shape)
        
        # 嘗試踢牆
        for dx, dy in KICK_OFFSETS:
            if not self.check_collision(new_shape, self.cx + dx, self.cy + dy):
                self.current_shape = new_shape
                self.cx += dx
                self.cy += dy
                self.play_sound(600, 10)
                self.reset_lock_delay()
                return # 成功就結束
                
    def reset_lock_delay(self):
        # 只要有成功操作，且在地板上，且次數未滿，重置鎖定計時
        if self.lock_timer is not None and self.moves_reset_cnt < 15:
            self.lock_timer = time.ticks_ms()
            self.moves_reset_cnt += 1

    def handle_hold(self):
        if self.hold_used: return
        
        self.play_sound(1000, 20)
        if self.hold_shape is None:
            # 第一次 Hold：存入當前，拿出 Next
            self.hold_shape = (self.current_shape, self.current_id)
            self.spawn_piece() # 這裡會把 Next 變成 Current
        else:
            # 交換
            temp = (self.current_shape, self.current_id)
            self.current_shape = self.hold_shape[0]
            self.current_id = self.hold_shape[1]
            self.hold_shape = temp
            
            # 重置位置
            self.cx = FIELD_W // 2 - len(self.current_shape[0]) // 2
            self.cy = -len(self.current_shape)
            self.lock_timer = None
            self.moves_reset_cnt = 0
            
        self.hold_used = True

    # --- T-Spin 偵測 ---
    def detect_t_spin(self):
        if self.current_id != 3: return False # 只有 T 塊才算
        # 檢查 T 方塊的四個角落 (Bounding Box 的 0,0 / 2,0 / 0,2 / 2,2)
        # 簡單判定：只要這四個角有 3 個以上被佔據（牆壁或方塊），且最後動作是旋轉，就算 T-Spin
        # 這裡簡化為檢查角落佔用，不嚴格檢查 "最後動作是旋轉" (因為這需要額外變數追蹤)
        
        corners = [(0,0), (2,0), (0,2), (2,2)]
        occupied = 0
        for dx, dy in corners:
            chk_x = self.cx + dx
            chk_y = self.cy + dy
            if chk_x < 0 or chk_x >= FIELD_W or chk_y >= FIELD_H:
                occupied += 1
            elif chk_y >= 0 and self.field[chk_y][chk_x]:
                occupied += 1
        
        return occupied >= 3

    # --- 遊戲循環與繪圖 ---
    def update(self):
        now = time.ticks_ms()
        dx, dy = self.inputs.read_axis()
        
        # 1. 處理移動與旋轉
        moved = False
        if dx != 0: 
            if not self.check_collision(self.current_shape, self.cx + dx, self.cy):
                self.cx += dx
                self.play_sound(400, 5)
                self.reset_lock_delay()
                moved = True
            time.sleep(0.05) # 簡單的移動延遲

        if dy == -1: # 上：旋轉
            self.try_rotate()
            time.sleep(0.15) # 旋轉冷卻
        
        if self.inputs.check_btn_press(): # 按鈕：Hold
            self.handle_hold()

        # 2. 處理下落與鎖定
        soft_drop = (dy == 1)
        # 如果按下，加速下落
        current_speed = self.fall_speed // 4 if soft_drop else self.fall_speed
        
        # 幽靈方塊位置計算 (Ghost Piece)
        ghost_y = self.cy
        while not self.check_collision(self.current_shape, self.cx, ghost_y + 1):
            ghost_y += 1
        
        # 檢查是否著地
        is_on_ground = self.check_collision(self.current_shape, self.cx, self.cy + 1)
        
        if is_on_ground:
            if self.lock_timer is None:
                self.lock_timer = now # 開始鎖定倒數
            
            # 鎖定時間到 或 強制下落
            if (now - self.lock_timer > self.lock_delay) or (soft_drop and now - self.last_fall_time > 50):
                self.lock_piece()
        else:
            self.lock_timer = None
            if now - self.last_fall_time > current_speed:
                self.cy += 1
                self.last_fall_time = now

    def lock_piece(self):
        # 檢查 T-Spin
        is_tspin = self.detect_t_spin()
        
        # 固定方塊
        for y, row in enumerate(self.current_shape):
            for x, val in enumerate(row):
                if val and self.cy + y >= 0:
                    self.field[self.cy + y][self.cx + x] = 1
        
        self.play_sound(150, 50) # 落地聲
        
        # 消除行與計分
        full_lines = []
        for y in range(FIELD_H):
            if all(self.field[y]):
                full_lines.append(y)
        
        if full_lines:
            self.play_sound_clear()
            # 視覺閃爍
            self.oled.fill_rect(OFFSET_X, full_lines[0]*BLOCK_SIZE, FIELD_W*BLOCK_SIZE, len(full_lines)*BLOCK_SIZE, 0)
            self.oled.show()
            time.sleep(0.1)
            
            # 移除行
            for fy in full_lines:
                del self.field[fy]
                self.field.insert(0, [0] * FIELD_W)
            
            # 計分邏輯 (含 T-Spin 加成)
            cnt = len(full_lines)
            base_score = [0, 100, 300, 500, 800] # 0, 1, 2, 3, 4 lines
            points = base_score[cnt]
            if is_tspin:
                points *= 2 # T-Spin 雙倍分
                self.draw_popup("T-SPIN!")
            
            self.score += points * self.level
            self.lines += cnt
            
            # 升級 (每 10 行)
            if self.lines // 10 >= self.level:
                self.level += 1
                self.fall_speed = max(100, 1000 - (self.level * 80))

        self.spawn_piece()

    def draw(self):
        self.oled.fill(0)
        
        # --- UI 框架 ---
        # 左側 Hold
        self.oled.text("H", 0, 0)
        self.oled.rect(0, 10, 26, 26, 1)
        if self.hold_shape:
            self.draw_mini_piece(self.hold_shape[0], 2, 12)
            
        # 中間遊戲區 (邊框)
        self.oled.rect(OFFSET_X - 2, 0, FIELD_W * BLOCK_SIZE + 4, 64, 1)
        
        # 右側 Next 與資訊
        self.oled.text("N", 90, 0)
        self.oled.rect(90, 10, 26, 26, 1)
        self.draw_mini_piece(self.next_shape_def[0], 92, 12)
        
        self.oled.text(f"{self.score}", 85, 40)
        self.oled.text(f"Lv{self.level}", 85, 50)

        # --- 遊戲內容 ---
        # 1. 已固定方塊
        for y in range(FIELD_H):
            for x in range(FIELD_W):
                if self.field[y][x]:
                    self.oled.fill_rect(OFFSET_X + x*BLOCK_SIZE, y*BLOCK_SIZE, BLOCK_SIZE-1, BLOCK_SIZE-1, 1)
        
        # 2. 幽靈方塊 (Ghost Piece) - 空心框
        ghost_y = self.cy
        while not self.check_collision(self.current_shape, self.cx, ghost_y + 1):
            ghost_y += 1
        
        for y, row in enumerate(self.current_shape):
            for x, val in enumerate(row):
                if val and ghost_y + y >= 0:
                     self.oled.rect(OFFSET_X + (self.cx+x)*BLOCK_SIZE, (ghost_y+y)*BLOCK_SIZE, BLOCK_SIZE-1, BLOCK_SIZE-1, 1)

        # 3. 當前移動方塊 (實心)
        for y, row in enumerate(self.current_shape):
            for x, val in enumerate(row):
                if val and self.cy + y >= 0:
                    self.oled.fill_rect(OFFSET_X + (self.cx+x)*BLOCK_SIZE, (self.cy+y)*BLOCK_SIZE, BLOCK_SIZE-1, BLOCK_SIZE-1, 1)
                    
        self.oled.show()

    def draw_mini_piece(self, shape, ox, oy):
        # 在 Hold/Next 框框中畫小方塊
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    self.oled.fill_rect(ox + x*4, oy + y*4, 3, 3, 1)

    def draw_popup(self, text):
        # 顯示短暫文字 (如 T-SPIN)
        self.oled.fill_rect(30, 25, 68, 14, 0) # 清空背景
        self.oled.rect(30, 25, 68, 14, 1)      # 框
        self.oled.text(text, 35, 28)
        self.oled.show()
        time.sleep(0.5)

    # --- 音效 ---
    def play_sound(self, freq, duration_ms):
        if self.buzzer:
            self.buzzer.freq(freq)
            self.buzzer.duty_u16(5000)
            time.sleep_ms(duration_ms)
            self.buzzer.duty_u16(0)

    def play_sound_clear(self):
        notes = [880, 1175, 1760]
        for n in notes:
            self.buzzer.freq(n); self.buzzer.duty_u16(10000)
            time.sleep(0.08)
        self.buzzer.duty_u16(0)

# ==============================================
# 主程式
# ==============================================
if __name__ == "__main__":
    print("Tetris Enhanced Loading...")
    display = DisplayUnit()
    inputs = InputUnit()
    game = TetrisGame(display, inputs)
    
    try:
        while True:
            if not game.game_over:
                game.update()
                game.draw()
            else:
                # Game Over 畫面
                display.oled.fill(0)
                display.oled.text("GAME OVER", 30, 20)
                display.oled.text(f"Score:{game.score}", 30, 35)
                display.oled.text("Btn: Retry", 25, 50)
                display.oled.show()
                
                # 等待按鈕重來
                while not inputs.check_btn_press():
                    time.sleep(0.05)
                game.reset_game()
                
    except KeyboardInterrupt:
        print("Exit")
    except Exception as e:
        print(e)