from machine import Pin, ADC, PWM
import time
import random

# ==============================================
# 儲存 / 讀取紀錄
# ==============================================
def save_best(filename, score):
    try:
        with open(filename, "r") as fp:
            old = fp.read().strip()
            if old:
                old = int(old)
                if score >= old: return
    except:
        pass
    with open(filename, "w") as fp:
        fp.write(str(score))

# --- 遊戲常數 ---
PLAYER_SIZE = 3      
BLOCK_SIZE = 8        
WIDTH = 128
HEIGHT = 64
MAX_LIVES = 3  # [固定] 所有難度都是 3 條血

# ==============================================
# 難度設定 (地圖與怪物)
# 1 = 牆壁, 0 = 路, 2 = 出口
# ==============================================
LEVEL_DATA = {
    "easy": {
        "map": [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1], # 路很直，出口在右邊
            [1,0,1,1,1,1,1,1,1,1,1,1,1,1,0,1],
            [1,0,1,0,0,0,0,0,0,0,0,0,0,1,0,1],
            [1,0,1,0,1,1,1,1,1,1,1,1,0,1,0,1],
            [1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,1],
            [1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1], 
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        ],
        "monsters": [
            {'x': 60, 'y': 10, 'vx': 2, 'vy': 0}, # 只有兩隻怪物
            {'x': 60, 'y': 40, 'vx': -2, 'vy': 0}
        ],
        "file": "best_maze_easy.txt"
    },
    "normal": {
        "map": [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1],
            [1,0,1,1,1,0,1,0,1,1,1,1,1,1,0,1],
            [1,0,1,0,0,0,0,0,0,0,0,0,0,1,0,1],
            [1,0,1,0,1,1,1,1,1,1,1,1,0,1,0,1],
            [1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,1],
            [1,1,1,0,1,0,1,1,1,1,1,1,1,1,2,1], # 原始地圖
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        ],
        "monsters": [
            {'x': 40, 'y': 10, 'vx': 2, 'vy': 0},
            {'x': 80, 'y': 40, 'vx': 0, 'vy': 2},
            {'x': 60, 'y': 40, 'vx': -2, 'vy': 0}
        ],
        "file": "best_maze_normal.txt"
    },
    "hard": {
        "map": [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,1,0,0,0,0,0,0,0,0,0,0,0,2,1], # 路很窄
            [1,0,1,0,1,1,1,0,1,0,1,1,1,1,0,1],
            [1,0,0,0,1,0,0,0,1,0,0,0,0,0,0,1],
            [1,1,0,0,1,1,1,1,1,1,1,1,0,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1],
            [1,1,1,1,1,1,1,0,1,1,1,1,1,1,0,1], 
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        ],
        "monsters": [
            {'x': 30, 'y': 10, 'vx': 2, 'vy': 0},
            {'x': 90, 'y': 10, 'vx': 0, 'vy': 2}, # 垂直移動
            {'x': 50, 'y': 40, 'vx': 2, 'vy': 0},
            {'x': 20, 'y': 25, 'vx': 0, 'vy': 2}  # 第四隻怪
        ],
        "file": "best_maze_hard.txt"
    }
}

# 全域變數 placeholder
current_map = []
current_monsters = []
current_file = ""
px, py = 10, 10
lives = MAX_LIVES
oled = None
buzzer = None

# --- 音效函式 (保持不變) ---
def play_tone(freq, duration):
    if buzzer:
        if freq > 0:
            buzzer.freq(int(freq))
            buzzer.duty_u16(32768)
        else:
            buzzer.duty_u16(0)
        time.sleep(duration)
        buzzer.duty_u16(0)
        time.sleep(0.05)

def sound_damage():
    play_tone(150, 0.1)
    play_tone(100, 0.2)

def sound_alert():
    if buzzer:
        for _ in range(3): 
            for _ in range(20): 
                buzzer.duty_u16(32768)
                buzzer.freq(853)        
                time.sleep(0.025)        
                buzzer.freq(960)        
                time.sleep(0.025)        
            buzzer.duty_u16(0)          
            time.sleep(0.3)              

def sound_win():
    notes = [262, 262, 294, 262, 349, 330, 262, 262, 294, 262, 392, 349]
    beats = [0.4, 0.4, 0.6, 0.6, 0.6, 1.0, 0.4, 0.4, 0.6, 0.6, 0.6, 1.0]
    for f, t in zip(notes, beats):
        play_tone(f, t)

# --- 遊戲繪圖與邏輯 ---
def draw_maze():
    for row in range(len(current_map)):
        for col in range(len(current_map[0])):
            block = current_map[row][col]
            x = col * BLOCK_SIZE
            y = row * BLOCK_SIZE
            if block == 1:
                oled.fill_rect(x, y, BLOCK_SIZE, BLOCK_SIZE, 1)
            elif block == 2:
                oled.rect(x, y, BLOCK_SIZE, BLOCK_SIZE, 1)
                oled.fill_rect(x+2, y+2, BLOCK_SIZE-4, BLOCK_SIZE-4, 1)

def draw_hud(start_time):
    elapsed = int(time.time() - start_time)
    msg = f"HP:{lives} T:{elapsed}s"
    oled.fill_rect(0, 0, 80, 10, 0) 
    oled.text(msg, 0, 0, 1)

def draw_monsters():
    for m in current_monsters:
        oled.rect(m['x'], m['y'], PLAYER_SIZE+2, PLAYER_SIZE+2, 1)

def check_collision(new_x, new_y):
    corners = [
        (new_x, new_y), (new_x + PLAYER_SIZE, new_y),
        (new_x, new_y + PLAYER_SIZE), (new_x + PLAYER_SIZE, new_y + PLAYER_SIZE)
    ]
    for x, y in corners:
        gx = int(x / BLOCK_SIZE)
        gy = int(y / BLOCK_SIZE)
        if gy < 0 or gy >= len(current_map) or gx < 0 or gx >= len(current_map[0]): return True
        if current_map[gy][gx] == 1: return True
    return False

def move_monsters():
    for m in current_monsters:
        next_x = m['x'] + m['vx']
        next_y = m['y'] + m['vy']
        if check_collision(next_x, next_y):
            m['vx'] = -m['vx']
            m['vy'] = -m['vy']
        else:
            m['x'] = next_x
            m['y'] = next_y

def check_win(p_x, p_y):
    center_x = p_x + PLAYER_SIZE // 2
    center_y = p_y + PLAYER_SIZE // 2
    gx = int(center_x / BLOCK_SIZE)
    gy = int(center_y / BLOCK_SIZE)
    if 0 <= gy < len(current_map) and 0 <= gx < len(current_map[0]):
        if current_map[gy][gx] == 2:
            return True
    return False

def check_hit(p_x, p_y):
    for m in current_monsters:
        m_w = PLAYER_SIZE + 2
        if (p_x < m['x'] + m_w and p_x + PLAYER_SIZE > m['x'] and
            p_y < m['y'] + m_w and p_y + PLAYER_SIZE > m['y']):
            return True
    return False

def reset_positions():
    global px, py
    px = 10
    py = 10

def reset_game(difficulty_key):
    global lives, current_monsters, current_map, current_file
    lives = MAX_LIVES
    reset_positions()
    
    # 根據難度載入資料
    data = LEVEL_DATA[difficulty_key]
    current_map = data["map"]
    current_file = data["file"]
    
    # 深層複製怪物列表，確保重置時回到初始狀態
    current_monsters = []
    for m in data["monsters"]:
        current_monsters.append(m.copy())

def show_screen(title, subtitle):
    oled.fill(0)
    oled.text(title, 30, 25, 1)
    oled.text(subtitle, 30, 40, 1)
    oled.show()

# =========================================
# 主要入口函式：新增 difficulty 參數
# =========================================
def start_maze_game(display_unit, input_unit, difficulty="normal"):
    global oled, buzzer, px, py, lives
    
    oled = display_unit.oled
    buzzer = PWM(Pin(9))
    buzzer.duty_u16(0)

    # 初始化該難度的遊戲
    reset_game(difficulty)
    
    start_time = time.time()

    while True:
        if input_unit.is_enter_pressed():
            buzzer.duty_u16(0)
            while input_unit.is_enter_pressed(): time.sleep(0.01)
            break 

        x_val = input_unit.read_joy_x()
        y_val = input_unit.read_joy_y()
        
        dx, dy = 0, 0
        if x_val < 20000: dx = -2 
        if x_val > 45000: dx = 2  
        if y_val < 20000: dy = -2 
        if y_val > 45000: dy = 2  
        
        if not check_collision(px + dx, py): px += dx
        if not check_collision(px, py + dy): py += dy

        move_monsters()

        oled.fill(0)
        draw_maze()
        draw_monsters()
        oled.fill_rect(px, py, PLAYER_SIZE, PLAYER_SIZE, 1)
        draw_hud(start_time) 
        oled.show()
        
        if check_win(px, py):
            final_time = int(time.time() - start_time)
            show_screen("You Win!", f"Time: {final_time}s") 
            sound_win() 
            save_best(current_file, final_time) # 存入對應難度的檔案
            time.sleep(2)
            
            reset_game(difficulty)
            start_time = time.time() 
            
        if check_hit(px, py):
            lives -= 1
            sound_damage() 
            
            if lives > 0:
                reset_positions()
                time.sleep(0.5) 
            else:
                sound_alert() 
                show_screen("GAME OVER", "Try Again")
                time.sleep(2)
                reset_game(difficulty)
                start_time = time.time()
        
        time.sleep(0.05)