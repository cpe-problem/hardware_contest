from machine import Pin, PWM
import time, random

# ==============================================
# 儲存紀錄
# ==============================================
def save_best(filename, score):
    try:
        with open(filename, "r") as fp:
            old = fp.read().strip()
            if old:
                old = int(old)
                if score <= old: return 
    except:
        pass
    with open(filename, "w") as fp:
        fp.write(str(score))

# --- 音效 ---
buzzer = None
def sound_move():
    if buzzer:
        buzzer.freq(400); buzzer.duty_u16(5000)
        time.sleep(0.01); buzzer.duty_u16(0)

def sound_rotate():
    if buzzer:
        buzzer.freq(600); buzzer.duty_u16(5000)
        time.sleep(0.01); buzzer.duty_u16(0)

def sound_land():
    if buzzer:
        buzzer.freq(150); buzzer.duty_u16(10000)
        time.sleep(0.05); buzzer.duty_u16(0)

def sound_clear():
    if buzzer:
        notes = [880, 1175, 1760] # A5, D6, A6
        for n in notes:
            buzzer.freq(n); buzzer.duty_u16(32768)
            time.sleep(0.08)
        buzzer.duty_u16(0)

# ==============================================
# 方塊定義 (4x4 矩陣表示)
# ==============================================
SHAPES = [
    [[1, 1, 1, 1]], # I (長條)
    
    [[1, 1], 
     [1, 1]],       # O (正方)
    
    [[0, 1, 0],
     [1, 1, 1]],    # T
     
    [[1, 0, 0],
     [1, 1, 1]],    # L
     
    [[0, 0, 1],
     [1, 1, 1]],    # J
     
    [[0, 1, 1],
     [1, 1, 0]],    # S
     
    [[1, 1, 0],
     [0, 1, 1]]     # Z
]

COLORS = [1, 1, 1, 1, 1, 1, 1] # 單色螢幕全是 1

# ==============================================
# Tetris 主邏輯
# ==============================================
def start_tetris_game(display_unit, input_unit):
    global buzzer
    oled = display_unit.oled
    buzzer = PWM(Pin(9))
    buzzer.duty_u16(0)

    # --- 參數設定 ---
    BLOCK_SIZE = 4       # 每個方塊 4x4 像素
    FIELD_W = 10         # 寬度 10 格
    FIELD_H = 16         # 高度 16 格 (16*4 = 64 pixels, 剛好滿屏)
    OFFSET_X = 2         # 畫面左邊留 2 pixel
    OFFSET_Y = 0
    
    # 遊戲區域 (0:空, 1:有方塊)
    field = [[0] * FIELD_W for _ in range(FIELD_H)]
    
    score = 0
    lines_cleared = 0
    game_over = False
    
    JOY_LOW = 15000
    JOY_HIGH = 50000
    
    # --- 輔助函式：檢查碰撞 ---
    def check_collision(shape, ox, oy):
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    # 檢查邊界
                    if ox + x < 0 or ox + x >= FIELD_W or oy + y >= FIELD_H:
                        return True
                    # 檢查是否重疊已存在的方塊 (忽略上方還沒進場的部分 oy+y < 0)
                    if oy + y >= 0 and field[oy + y][ox + x]:
                        return True
        return False

    # --- 輔助函式：將方塊固定到場地 ---
    def freeze_shape(shape, ox, oy):
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val and oy + y >= 0:
                    field[oy + y][ox + x] = 1

    # --- 輔助函式：旋轉方塊 ---
    def rotate_shape(shape):
        return [list(row) for row in zip(*shape[::-1])]

    # --- 生成新方塊 ---
    def new_piece():
        idx = random.randint(0, len(SHAPES) - 1)
        shape = SHAPES[idx]
        # 初始位置：中間上方
        px = FIELD_W // 2 - len(shape[0]) // 2
        py = -len(shape) # 從畫面外開始
        return shape, px, py

    current_shape, cx, cy = new_piece()
    
    # 遊戲迴圈控制
    fall_speed = 15      # 自動掉落速度 (幀數)
    fall_counter = 0
    input_delay = 0      # 按鍵冷卻

    while True:
        if input_unit.is_enter_pressed():
            buzzer.duty_u16(0)
            while input_unit.is_enter_pressed(): time.sleep(0.01)
            return

        if not game_over:
            # === 輸入處理 ===
            jx = input_unit.read_joy_x()
            jy = input_unit.read_joy_y()
            
            # 左右移動 (帶延遲避免跑太快)
            if input_delay == 0:
                if jx < JOY_LOW:
                    if not check_collision(current_shape, cx - 1, cy):
                        cx -= 1
                        sound_move()
                        input_delay = 3
                elif jx > JOY_HIGH:
                    if not check_collision(current_shape, cx + 1, cy):
                        cx += 1
                        sound_move()
                        input_delay = 3
                
                # 旋轉 (搖桿往上)
                if jy < JOY_LOW:
                    rotated = rotate_shape(current_shape)
                    if not check_collision(rotated, cx, cy):
                        current_shape = rotated
                        sound_rotate()
                        input_delay = 5 # 旋轉冷卻長一點
                        
                # 加速掉落 (搖桿往下)
                if jy > JOY_HIGH:
                    fall_counter = fall_speed # 強制觸發掉落
            
            if input_delay > 0: input_delay -= 1

            # === 自動掉落機制 ===
            fall_counter += 1
            if fall_counter >= fall_speed:
                fall_counter = 0
                if not check_collision(current_shape, cx, cy + 1):
                    cy += 1
                else:
                    # 落地
                    sound_land()
                    freeze_shape(current_shape, cx, cy)
                    
                    # 檢查是否輸了 (方塊還在頂部就碰撞)
                    if cy < 0:
                        game_over = True
                    else:
                        # === 消除行檢查 ===
                        full_lines = []
                        for y in range(FIELD_H):
                            if all(field[y]): # 整行都是 1
                                full_lines.append(y)
                        
                        if full_lines:
                            sound_clear()
                            # 視覺特效：閃爍消除的行
                            for _ in range(3):
                                oled.fill(0)
                                # 畫邊框
                                oled.rect(0, 0, FIELD_W*BLOCK_SIZE + 4, 64, 1)
                                # 只畫這幾行
                                for fy in full_lines:
                                    oled.fill_rect(OFFSET_X, fy*BLOCK_SIZE, FIELD_W*BLOCK_SIZE, BLOCK_SIZE, 1)
                                oled.show()
                                time.sleep(0.05)
                                oled.fill(0)
                                oled.show()
                                time.sleep(0.05)
                            
                            # 移除行並下墜
                            for fy in full_lines:
                                del field[fy]
                                field.insert(0, [0] * FIELD_W) # 補空行在頂部
                            
                            # 計分 (1行10, 2行30, 3行60, 4行100)
                            count = len(full_lines)
                            score += count * 10 * count
                            lines_cleared += count
                            
                            # 難度增加
                            if lines_cleared > 5: fall_speed = 12
                            if lines_cleared > 10: fall_speed = 10
                            if lines_cleared > 20: fall_speed = 5

                        # 生成新方塊
                        current_shape, cx, cy = new_piece()

            # === 繪圖 ===
            oled.fill(0)
            
            # 1. 畫邊框 (左側遊戲區)
            # 寬度 = 10格 * 4pixel + 邊框線
            game_w_px = FIELD_W * BLOCK_SIZE
            oled.rect(0, 0, game_w_px + 4, 64, 1)
            
            # 2. 畫已固定的方塊
            for y in range(FIELD_H):
                for x in range(FIELD_W):
                    if field[y][x]:
                        # 實心方塊
                        oled.fill_rect(OFFSET_X + x*BLOCK_SIZE, OFFSET_Y + y*BLOCK_SIZE, BLOCK_SIZE-1, BLOCK_SIZE-1, 1)

            # 3. 畫當前移動中的方塊
            for y, row in enumerate(current_shape):
                for x, val in enumerate(row):
                    if val:
                        draw_x = OFFSET_X + (cx + x) * BLOCK_SIZE
                        draw_y = OFFSET_Y + (cy + y) * BLOCK_SIZE
                        # 只畫在畫面內的
                        if draw_y >= 0:
                            oled.fill_rect(draw_x, draw_y, BLOCK_SIZE-1, BLOCK_SIZE-1, 1)

            # 4. 畫 UI (右側)
            ui_x = game_w_px + 6
            oled.text("TETRIS", ui_x, 0)
            oled.text(f"Sc:{score}", ui_x, 15)
            oled.text(f"Ln:{lines_cleared}", ui_x, 25)
            
            # 顯示下一個難度提示
            oled.text(f"Spd:{16-fall_speed}", ui_x, 40) # 數字越大越快

            oled.show()
            time.sleep(0.02) # 50 FPS

        else:
            # 遊戲結束
            oled.fill(0)
            oled.text("GAME OVER", 25, 20)
            oled.text(f"Score: {score}", 25, 40)
            oled.show()
            save_best("best_tetris.txt", score)
            
            time.sleep(2)
            while not input_unit.is_enter_pressed(): pass
            while input_unit.is_enter_pressed(): pass
            return