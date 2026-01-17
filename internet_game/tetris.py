from machine import Pin, PWM, I2C, ADC
import time, random
import ssd1306

# ==============================================
# 硬體驅動層
# ==============================================
class DisplayUnit:
    def __init__(self):
        # I2C 設定 (SDA=GP14, SCL=GP15)
        self.i2c = I2C(1, sda=Pin(14), scl=Pin(15), freq=400000)
        self.oled = ssd1306.SSD1306_I2C(128, 64, self.i2c)

class InputUnit:
    def __init__(self):
        self.joy_x = ADC(Pin(26))
        self.joy_y = ADC(Pin(27))
        self.btn = Pin(16, Pin.IN, Pin.PULL_UP)
        
        self.btn_prev = 1
        self.press_start_time = 0
        self.action_triggered = False
        self.MIN = 15000
        self.MAX = 50000

    def read_axis(self):
        x_val, y_val = self.joy_x.read_u16(), self.joy_y.read_u16()
        dx, dy = 0, 0
        
        if x_val < self.MIN: dx = -1
        elif x_val > self.MAX: dx = 1
        
        if y_val < self.MIN: dy = -1 # 上 (旋轉)
        elif y_val > self.MAX: dy = 1 # 下 (軟降)
        
        return dx, dy

    def check_btn_action(self):
        curr = self.btn.value()
        result = 'NONE'
        now = time.ticks_ms()

        if curr == 0 and self.btn_prev == 1:
            self.press_start_time = now
            self.action_triggered = False
        elif curr == 0 and self.btn_prev == 0:
            if not self.action_triggered and (now - self.press_start_time > 300):
                result = 'HOLD'
                self.action_triggered = True 
        elif curr == 1 and self.btn_prev == 0:
            if not self.action_triggered:
                result = 'CLICK'
        
        self.btn_prev = curr
        return result

# ==============================================
# 遊戲設定
# ==============================================
BLOCK_SIZE = 4
FIELD_W, FIELD_H = 10, 16
OFFSET_X = 34

SHAPES_DEF = [
    ([[1, 1, 1, 1]], 1),             # I
    ([[1, 1], [1, 1]], 2),           # O
    ([[0, 1, 0], [1, 1, 1]], 3),     # T
    ([[1, 0, 0], [1, 1, 1]], 4),     # L
    ([[0, 0, 1], [1, 1, 1]], 5),     # J
    ([[0, 1, 1], [1, 1, 0]], 6),     # S
    ([[1, 1, 0], [0, 1, 1]], 7)      # Z
]
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
        
        self.bag = []
        self.hold_shape = None
        self.hold_used = False
        
        self.next_shape_def = self.get_from_bag()
        self.spawn_piece()
        
        self.fall_speed = 1000
        self.last_fall_time = time.ticks_ms()
        self.lock_delay = 500
        self.lock_timer = None
        self.moves_reset_cnt = 0

    def get_from_bag(self):
        if not self.bag:
            self.bag = list(SHAPES_DEF)
        idx = random.randint(0, len(self.bag) - 1)
        return self.bag.pop(idx)

    def spawn_piece(self):
        self.current_shape = self.next_shape_def[0]
        self.current_id = self.next_shape_def[1]
        self.next_shape_def = self.get_from_bag()
        
        self.cx = FIELD_W // 2 - len(self.current_shape[0]) // 2
        self.cy = -len(self.current_shape) # 從畫面外生成
        
        self.hold_used = False
        self.lock_timer = None
        self.moves_reset_cnt = 0

        # 如果生成時已經碰撞 (例如場地已滿到最頂)，直接結束
        if self.check_collision(self.current_shape, self.cx, self.cy):
            self.game_over = True

    def check_collision(self, shape, ox, oy):
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    bx, by = ox + x, oy + y
                    if bx < 0 or bx >= FIELD_W or by >= FIELD_H: return True
                    # 只檢查畫面內的碰撞
                    if by >= 0 and self.field[by][bx]: return True
        return False

    def rotate_matrix(self, shape):
        return [list(row) for row in zip(*shape[::-1])]

    def try_rotate(self):
        new_shape = self.rotate_matrix(self.current_shape)
        for dx, dy in KICK_OFFSETS:
            if not self.check_collision(new_shape, self.cx + dx, self.cy + dy):
                self.current_shape = new_shape
                self.cx += dx
                self.cy += dy
                self.play_sound(600, 10)
                self.reset_lock_delay()
                return

    def reset_lock_delay(self):
        if self.lock_timer is not None and self.moves_reset_cnt < 15:
            self.lock_timer = time.ticks_ms()
            self.moves_reset_cnt += 1

    def handle_hold(self):
        if self.hold_used: return
        self.play_sound(1000, 20)
        self.draw_popup("HOLD")
        if self.hold_shape is None:
            self.hold_shape = (self.current_shape, self.current_id)
            self.spawn_piece()
        else:
            self.hold_shape, (self.current_shape, self.current_id) = (self.current_shape, self.current_id), self.hold_shape
            self.cx = FIELD_W // 2 - len(self.current_shape[0]) // 2
            self.cy = -len(self.current_shape)
            self.lock_timer = None
            self.moves_reset_cnt = 0
        self.hold_used = True

    def hard_drop(self):
        dist = 0
        while not self.check_collision(self.current_shape, self.cx, self.cy + dist + 1):
            dist += 1
        self.cy += dist
        self.score += dist * 2
        self.play_sound(1500, 30)
        self.lock_piece()

    def detect_t_spin(self):
        if self.current_id != 3: return False
        corners = [(0,0), (2,0), (0,2), (2,2)]
        occupied = 0
        for dx, dy in corners:
            chk_x, chk_y = self.cx + dx, self.cy + dy
            if chk_x < 0 or chk_x >= FIELD_W or chk_y >= FIELD_H: occupied += 1
            elif chk_y >= 0 and self.field[chk_y][chk_x]: occupied += 1
        return occupied >= 3

    # ==========================
    # 核心修復：鎖定與 Game Over 判定
    # ==========================
    def lock_piece(self):
        # 1. 檢查是否溢出天花板 (Game Over 核心判定)
        # 如果方塊要鎖定，但有任何一部分還在負數座標(畫面外)，代表堆滿了
        for y, row in enumerate(self.current_shape):
            for x, val in enumerate(row):
                if val and (self.cy + y < 0):
                    self.game_over = True
                    self.play_sound(100, 500) # 死亡音效
                    return # 直接結束，不進行後續寫入

        # 2. 正常寫入場地
        is_tspin = self.detect_t_spin()
        for y, row in enumerate(self.current_shape):
            for x, val in enumerate(row):
                if val and self.cy + y >= 0:
                    self.field[self.cy + y][self.cx + x] = 1
        
        self.play_sound(150, 50)
        
        # 3. 消除判定
        full_lines = [y for y in range(FIELD_H) if all(self.field[y])]
        if full_lines:
            self.play_sound_clear()
            self.oled.fill_rect(OFFSET_X, full_lines[0]*BLOCK_SIZE, FIELD_W*BLOCK_SIZE, len(full_lines)*BLOCK_SIZE, 0)
            self.oled.show()
            time.sleep(0.05)
            
            for fy in full_lines:
                del self.field[fy]
                self.field.insert(0, [0] * FIELD_W)
            
            pts = [0, 100, 300, 500, 800][len(full_lines)]
            if is_tspin:
                pts *= 2
                self.draw_popup("T-SPIN!")
            self.score += pts * self.level
            self.lines += len(full_lines)
            
            if self.lines // 10 >= self.level:
                self.level += 1
                self.fall_speed = max(100, 1000 - (self.level * 80))

        self.spawn_piece()

    def update(self):
        now = time.ticks_ms()
        dx, dy = self.inputs.read_axis()
        btn_action = self.inputs.check_btn_action()

        if btn_action == 'HOLD':
            self.handle_hold()
        elif btn_action == 'CLICK':
            self.hard_drop()
            return

        if dx != 0: 
            if not self.check_collision(self.current_shape, self.cx + dx, self.cy):
                self.cx += dx
                self.play_sound(400, 5)
                self.reset_lock_delay()
            time.sleep(0.05)

        if dy == -1: 
            self.try_rotate()
            time.sleep(0.15)

        soft_drop = (dy == 1)
        current_speed = self.fall_speed // 6 if soft_drop else self.fall_speed
        if soft_drop: self.score += 1

        is_on_ground = self.check_collision(self.current_shape, self.cx, self.cy + 1)
        
        if is_on_ground:
            if self.lock_timer is None: self.lock_timer = now
            if (now - self.lock_timer > self.lock_delay) or (soft_drop and now - self.last_fall_time > 50):
                self.lock_piece()
        else:
            self.lock_timer = None
            if now - self.last_fall_time > current_speed:
                self.cy += 1
                self.last_fall_time = now

    def draw(self):
        self.oled.fill(0)
        
        # UI
        self.oled.text("H", 0, 0); self.oled.rect(0, 10, 26, 26, 1)
        if self.hold_shape: self.draw_mini_piece(self.hold_shape[0], 2, 12)
        
        self.oled.text("N", 90, 0); self.oled.rect(90, 10, 26, 26, 1)
        self.draw_mini_piece(self.next_shape_def[0], 92, 12)
        
        self.oled.text(f"{self.score}", 85, 40)
        self.oled.text(f"Lv{self.level}", 85, 50)

        # Game Field
        self.oled.rect(OFFSET_X - 2, 0, FIELD_W * BLOCK_SIZE + 4, 64, 1)
        for y in range(FIELD_H):
            for x in range(FIELD_W):
                if self.field[y][x]:
                    self.oled.fill_rect(OFFSET_X + x*BLOCK_SIZE, y*BLOCK_SIZE, BLOCK_SIZE-1, BLOCK_SIZE-1, 1)
        
        # Ghost Piece
        ghost_y = self.cy
        while not self.check_collision(self.current_shape, self.cx, ghost_y + 1): ghost_y += 1
        for y, row in enumerate(self.current_shape):
            for x, val in enumerate(row):
                if val and ghost_y+y >= 0:
                    self.oled.rect(OFFSET_X+(self.cx+x)*BLOCK_SIZE, (ghost_y+y)*BLOCK_SIZE, BLOCK_SIZE-1, BLOCK_SIZE-1, 1)

        # Current Piece
        for y, row in enumerate(self.current_shape):
            for x, val in enumerate(row):
                if val and self.cy+y >= 0:
                    self.oled.fill_rect(OFFSET_X+(self.cx+x)*BLOCK_SIZE, (self.cy+y)*BLOCK_SIZE, BLOCK_SIZE-1, BLOCK_SIZE-1, 1)
        self.oled.show()

    def draw_mini_piece(self, shape, ox, oy):
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val: self.oled.fill_rect(ox + x*4, oy + y*4, 3, 3, 1)

    def draw_popup(self, text):
        self.oled.fill_rect(20, 25, 88, 14, 0)
        self.oled.rect(20, 25, 88, 14, 1)
        self.oled.text(text, 35, 28)
        self.oled.show()
        time.sleep(0.3)

    def play_sound(self, freq, d):
        if self.buzzer: self.buzzer.freq(freq); self.buzzer.duty_u16(5000); time.sleep_ms(d); self.buzzer.duty_u16(0)
    
    def play_sound_clear(self):
        for n in [880, 1175, 1760]: self.play_sound(n, 80)

if __name__ == "__main__":
    game = TetrisGame(DisplayUnit(), InputUnit())
    while True:
        if not game.game_over:
            game.update()
            game.draw()
        else:
            # Game Over 畫面
            game.oled.fill(0)
            game.oled.text("GAME OVER", 30, 20)
            game.oled.text(f"Score:{game.score}", 30, 35)
            game.oled.text("Click to Retry", 10, 50)
            game.oled.show()
            
            time.sleep(0.1)
            # 等按鈕重來
            if game.inputs.check_btn_action() == 'CLICK': 
                game.reset_game()
