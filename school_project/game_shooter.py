from machine import Pin, PWM
import time, random

# ==============================================
# 儲存 / 讀取紀錄
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

# ==============================================
# 音效區
# ==============================================
buzzer = None

def sound_shoot():
    if buzzer:
        buzzer.freq(900)
        buzzer.duty_u16(10000) 
        time.sleep(0.01)
        buzzer.duty_u16(0)

def sound_hit():
    if buzzer:
        buzzer.freq(400)
        buzzer.duty_u16(10000)
        time.sleep(0.02)
        buzzer.duty_u16(0)

def sound_explosion():
    if buzzer:
        for f in range(200, 50, -20):
            buzzer.freq(f)
            buzzer.duty_u16(32768)
            time.sleep(0.01)
        buzzer.duty_u16(0)

def sound_win():
    if buzzer:
        notes = [523, 659, 784, 1046]
        for n in notes:
            buzzer.freq(n)
            buzzer.duty_u16(32768)
            time.sleep(0.1)
        time.sleep(0.2)
        buzzer.duty_u16(0)

# ==============================================
# 主遊戲邏輯
# ==============================================
def start_shooter_game(display_unit, input_unit):
    global buzzer
    oled = display_unit.oled
    
    # ----------------------------------------------------
    # ★ 硬體設定確認 (根據你的最新回報) ★
    # ----------------------------------------------------
    # 1. 蜂鳴器設定在 GP9
    try:
        buzzer = PWM(Pin(9)) 
        buzzer.duty_u16(0)
    except Exception as e:
        print("Buzzer error:", e)

    # 2. 射擊按鈕設定在 GP7
    BTN_PIN_ID = 7 
    btn_fire = Pin(BTN_PIN_ID, Pin.IN, Pin.PULL_UP)
    
    print(f"Game Start! Button on GP{BTN_PIN_ID}, Buzzer on GP9")

    # --- 遊戲參數 ---
    ship_x = 60
    ship_y = 54
    ship_w = 8
    ship_h = 6
    
    bullets = [] 
    enemies = [] 
    
    score = 0
    lives = 3
    
    frame = 0
    spawn_rate = 50 
    enemy_speed = 0.6
    
    JOY_LOW = 15000
    JOY_HIGH = 50000

    game_over = False
    
    # 用來計算退出按鈕的長按時間
    exit_press_start = 0 

    while True:
        # 0. 檢查退出 (邏輯修改：需要長按 1.5 秒才能退出)
        # 這樣避免你想射擊(短按)時卻誤觸退出
        if input_unit.is_enter_pressed():
            if exit_press_start == 0:
                exit_press_start = time.ticks_ms()
            
            # 如果按住超過 1500ms (1.5秒) 則退出
            if time.ticks_diff(time.ticks_ms(), exit_press_start) > 1500:
                oled.fill(0)
                oled.text("Exiting...", 30, 30)
                oled.show()
                buzzer.duty_u16(0)
                time.sleep(1)
                return 
        else:
            exit_press_start = 0 # 放開按鈕，重置計時

        if not game_over:
            # 勝利判定
            if score >= 400:
                oled.fill(0)
                oled.text("MISSION", 35, 20)
                oled.text("COMPLETE!", 30, 35)
                oled.text(f"Score: {score}", 25, 50)
                oled.show()
                sound_win()
                save_best("best_shooter.txt", score)
                time.sleep(3)
                # 離開前等待
                while not input_unit.is_enter_pressed(): pass
                return

            # 1. 玩家移動
            jx = input_unit.read_joy_x()
            if jx < JOY_LOW:
                ship_x -= 3
            elif jx > JOY_HIGH:
                ship_x += 3
            ship_x = max(0, min(128 - ship_w, ship_x))

            # 2. 發射子彈
            jy = input_unit.read_joy_y()
            
            # 判斷是否觸發射擊 (GP7 按下 OR 搖桿上推)
            # btn_fire.value() == 0 代表按下 (因為是 PULL_UP)
            is_firing = (btn_fire.value() == 0) or (jy < JOY_LOW)
            
            if is_firing: 
                if frame % 5 == 0: # 限制射速
                    bullets.append([ship_x + ship_w//2, ship_y])
                    sound_shoot()

            # 3. 生成敵人
            level = 1 + (score // 100)
            enemy_speed = 0.6 + (score // 100) * 0.4
            if enemy_speed > 3.0: enemy_speed = 3.0
            
            if score > 100: spawn_rate = 40
            if score > 200: spawn_rate = 30
            if score > 300: spawn_rate = 20

            if frame % spawn_rate == 0:
                ex = random.randint(0, 120)
                enemies.append([float(ex), 0.0])

            # 4. 更新子彈
            for b in bullets:
                b[1] -= 4 
            bullets = [b for b in bullets if b[1] > 0]

            # 5. 更新敵人
            for e in enemies:
                e[1] += enemy_speed 
                if frame % 4 == 0:
                    e[0] += random.choice([-1, 1])

            # 6. 判定命中
            new_bullets = []
            hit_indices = []
            for b in bullets:
                hit = False
                for i, e in enumerate(enemies):
                    if i in hit_indices: continue
                    if (e[0] <= b[0] <= e[0] + 8) and (e[1] <= b[1] <= e[1] + 8):
                        hit_indices.append(i)
                        hit = True
                        score += 10
                        sound_hit()
                        break 
                if not hit:
                    new_bullets.append(b)
            bullets = new_bullets
            enemies = [e for i, e in enumerate(enemies) if i not in hit_indices]

            # 7. 判定受傷
            new_enemies = []
            for e in enemies:
                if e[1] > 60: # 撞底
                    lives -= 1
                    sound_explosion()
                    if lives <= 0: game_over = True
                    continue 
                
                if (ship_x < e[0] + 8 and ship_x + ship_w > e[0] and
                    ship_y < e[1] + 8 and ship_y + ship_h > e[1]): # 撞船
                    lives -= 1
                    sound_explosion()
                    time.sleep(0.5) 
                    new_enemies = [] 
                    bullets = []
                    if lives <= 0: game_over = True
                    break 
                else:
                    new_enemies.append(e)
            
            if not game_over:
                enemies = new_enemies

            # --- 繪圖 ---
            oled.fill(0)
            oled.line(int(ship_x + ship_w//2), ship_y, int(ship_x), ship_y + ship_h, 1)
            oled.line(int(ship_x + ship_w//2), ship_y, int(ship_x + ship_w), ship_y + ship_h, 1)
            oled.line(int(ship_x), ship_y + ship_h, int(ship_x + ship_w), ship_y + ship_h, 1)

            for b in bullets:
                oled.pixel(int(b[0]), int(b[1]), 1)
                oled.pixel(int(b[0]), int(b[1])+1, 1)

            for e in enemies:
                oled.rect(int(e[0]), int(e[1]), 8, 8, 1)

            oled.text(f"Sc:{score}", 0, 0)
            oled.text(f"Lv{level}", 55, 0)
            oled.text(f"HP:{lives}", 90, 0)
            oled.show()
            
            frame += 1
            time.sleep(0.02)

        else:
            # Game Over
            oled.fill(0)
            oled.text("GAME OVER", 25, 20)
            oled.text(f"Score: {score}", 25, 40)
            oled.show()
            save_best("best_shooter.txt", score)
            
            buzzer.duty_u16(0)
            time.sleep(2)
            
            # 結束後也需要長按才能真正離開
            # 或者這裡直接等按鍵放開再按一下
            while not input_unit.is_enter_pressed(): pass
            return