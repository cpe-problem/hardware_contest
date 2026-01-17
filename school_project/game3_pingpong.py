from machine import Pin
import time, urandom

# ============================================
# 單搖桿桌球：Player vs AI
# ============================================

def start_table_tennis(display_unit, input_unit):
    # 1. 使用主程式傳入的 display 和 input_unit
    oled = display_unit.oled

    # ======== 額外按鍵 (殺球) ========
    # 注意：Pin 20 也是蜂鳴器，按殺球時可能會有點干擾，但功能上可以用
    btn_smash = Pin(20, Pin.IN, Pin.PULL_UP)

    # ======== 畫面控制 ========
    paddle_h = 12
    paddle_w = 3

    # ======== 球狀態 ========
    ball_x, ball_y = 64, 32
    vx, vy = 2, 1
    normal_speed = 2
    smash_speed = 5
    curve_y = 0          # 旋轉量

    # ======== 殺球 ========
    smash_until = 0

    # ======== AI 狀態 ========
    ai_y = 32
    ai_target = 32
    ai_speed = 1
    reaction_delay = 3

    # ======== 比賽機制（三戰兩勝） ========
    score1 = 0
    score2 = 0
    game_win = 0
    game_win_ai = 0

    serve_owner = 1
    serve_count = 0

    def reset_ball():
        nonlocal ball_x, ball_y, vx, vy, serve_owner, serve_count
        ball_x, ball_y = 64, 32
        vy = 1
        vx = normal_speed if serve_owner == 1 else -normal_speed
        serve_count += 1

        # Deuce 換發邏輯
        if score1 < 10 and score2 < 10:
            if serve_count >= 2:
                serve_owner = 2 if serve_owner == 1 else 1
                serve_count = 0
        else:
            if serve_count >= 1:
                serve_owner = 2 if serve_owner == 1 else 1
                serve_count = 0

    reset_ball()
    frame = 0

    while True:
        frame += 1

        # ===== [修正] 退出遊戲 =====
        # 改用搖桿按鈕 is_enter_pressed()
        if input_unit.is_enter_pressed():
            # 等待放開，避免誤觸選單
            while input_unit.is_enter_pressed():
                time.sleep(0.01)
            return

        # ===== [修正] 玩家移動 =====
        # 使用搖桿 Y 軸 (0~65535) 映射到 螢幕高度 (0~52)
        # 注意：如果發現方向相反，可以用 (65535 - input_unit.read_joy_y()) 來反轉
        user_y = input_unit.read_joy_y() * (64 - paddle_h) // 65535

        # ===== 殺球按鍵 (維持 Pin 20) =====
        if btn_smash.value() == 0:
            smash_until = time.ticks_ms() + 250

        now = time.ticks_ms()
        if now < smash_until and vx < 0:
            vx = -smash_speed
        else:
            vx = -normal_speed if vx < 0 else normal_speed

        # ===== [修正] 旋轉球 (Curve) =====
        # 使用搖桿 X 軸來控制球的垂直漂移 (模擬旋球)
        # 中間值約 32768，左右偏移產生 curve_y
        curve_y = int((input_unit.read_joy_x() - 32768) / 8192)  # 範圍約 -4 ~ +4

        # ===== AI 移動 =====
        if frame % reaction_delay == 0:
            ai_target = ball_y - paddle_h // 2

        if ai_y < ai_target:
            ai_y += ai_speed
        elif ai_y > ai_target:
            ai_y -= ai_speed

        ai_y = min(max(ai_y, 0), 64 - paddle_h)

        # ===== 畫面更新 =====
        oled.fill(0)

        # 顯示比分
        oled.text(f"{game_win}", 0, 0)           # 玩家勝場
        oled.text(f"{score2}:{score1}", 48, 0)   # AI分數 : 玩家分數
        oled.text(f"{game_win_ai}", 115, 0)      # AI勝場

        # 繪製球拍與球
        oled.fill_rect(123, user_y, paddle_w, paddle_h, 1) # 玩家在右
        oled.fill_rect(2, ai_y, paddle_w, paddle_h, 1)     # AI 在左
        oled.fill_rect(int(ball_x), int(ball_y), 3, 3, 1)

        oled.show()

        # ===== 球物理運算 =====
        ball_x += vx
        ball_y += vy + curve_y  # 加上旋球效果

        # 隨機變向
        if frame % 6 == 0:
            ball_y += urandom.randint(-1, 1)

        # 上下牆壁反彈
        if ball_y <= 0 or ball_y >= 61:
            vy = -vy

        # AI 擋球判定
        if ball_x <= 5 and ai_y <= ball_y <= ai_y + paddle_h:
            vx = abs(vx)

        # 玩家擋球判定
        if ball_x >= 120 and user_y <= ball_y <= user_y + paddle_h:
            vx = -abs(vx)

        # ===== 得分判定與結束 =====
        def check_set_end():
            nonlocal score1, score2, game_win, game_win_ai
            if (score1 >= 11 or score2 >= 11) and abs(score1 - score2) >= 2:
                if score1 > score2:
                    game_win += 1
                else:
                    game_win_ai += 1
                score1 = 0
                score2 = 0
                return True
            return False

        # 玩家得分 (球在左邊出界)
        if ball_x < 0:
            score1 += 1
            if check_set_end():
                if game_win == 2:
                    oled.fill(0)
                    oled.text("YOU WIN!", 30, 28)
                    oled.show()
                    time.sleep(2)
                    return
            reset_ball()
            time.sleep(0.4)

        # AI 得分 (球在右邊出界)
        if ball_x > 128:
            score2 += 1
            if check_set_end():
                if game_win_ai == 2:
                    oled.fill(0)
                    oled.text("YOU LOSE", 30, 28)
                    oled.show()
                    time.sleep(2)
                    return
            reset_ball()
            time.sleep(0.4)

        time.sleep(0.012)