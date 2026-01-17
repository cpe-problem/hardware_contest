import time, urandom

# =====================================================
# 儲存 / 讀取紀錄 (維持不變)
# =====================================================
def save_best(filename, score):
    try:
        with open(filename, "r") as fp:
            old = fp.read().strip()
            if old:
                old = int(old)
                if score >= old:   # 必須比原本更少才算破紀錄
                    return
    except:
        pass

    with open(filename, "w") as fp:
        fp.write(str(score))

def load_best(filename):
    try:
        with open(filename, "r") as fp:
            data = fp.read().strip()
            if data:
                return int(data)
    except:
        return None
    return None


# =====================================================
# 單人模式 (改為搖桿操作)
# =====================================================
def guess_number_game(min_val, max_val, record_file, display_unit, input_unit):
    display = display_unit
    oled = display.oled
    
    # 產生謎底
    target = urandom.getrandbits(16) % (max_val - min_val + 1) + min_val

    low = min_val
    high = max_val
    count = 0
    
    # 預設猜測值設為中間，方便玩家調整
    guess = (low + high) // 2

    JOY_LOW = 15000
    JOY_HIGH = 50000

    while True:
        # --- 顯示畫面 ---
        oled.fill(0)
        oled.text("Guess Number", 0, 0)
        oled.text(f"Range: {low}-{high}", 0, 15)
        oled.text("Your Guess:", 0, 35)
        
        # 顯示大一點的數字
        oled.text(f"> {guess} <", 30, 48)
        oled.show()

        # --- 讀取搖桿 ---
        y_val = input_unit.read_joy_y()

        # 搖桿往上 -> 數字變大
        if y_val < JOY_LOW:
            if guess < high - 1: # 不能超過範圍
                guess += 1
                # 加速機制：如果範圍很大，可以按住不放跑快點
                if high - low > 100: 
                    time.sleep(0.05)
                else:
                    time.sleep(0.15)
            else:
                guess = high - 1 # 貼齊邊界

        # 搖桿往下 -> 數字變小
        elif y_val > JOY_HIGH:
            if guess > low + 1:
                guess -= 1
                if high - low > 100:
                    time.sleep(0.05)
                else:
                    time.sleep(0.15)
            else:
                guess = low + 1

        # --- 確認按鈕 ---
        if input_unit.is_enter_pressed():
            # 等待放開
            while input_unit.is_enter_pressed(): time.sleep(0.01)
            
            count += 1

            # 猜對了
            if guess == target:
                oled.fill(0)
                oled.text("Correct!", 30, 20)
                oled.text(f"Tries: {count}", 30, 40)
                oled.show()
                time.sleep(2)

                if record_file:
                    save_best(record_file, count)
                return

            # 猜太小
            elif guess < target:
                low = guess # 更新下限
                guess = (low + high) // 2 # 游標自動跳到新範圍中間
                oled.fill(0)
                oled.text("Too Low!", 30, 30)
                oled.show()
                time.sleep(0.8)

            # 猜太大
            else:
                high = guess # 更新上限
                guess = (low + high) // 2
                oled.fill(0)
                oled.text("Too High!", 30, 30)
                oled.show()
                time.sleep(0.8)


# =====================================================
# 多人模式 (P1 設定 -> P2 猜)
# =====================================================
def start_guess_versus(display_unit, input_unit):
    display = display_unit
    oled = display.oled
    
    # --- Phase 1: 玩家 1 設定答案 (類似 A/B Game 操作) ---
    digits = [0, 0, 0]
    index = 0
    JOY_LOW = 15000
    JOY_HIGH = 50000

    while True:
        oled.fill(0)
        oled.text("P1: Set Number", 0, 0)
        oled.text("(Don't Look P2)", 0, 10)

        num_str = "".join(str(d) for d in digits)
        oled.text(num_str, 50, 30)
        oled.text("^", 50 + index * 8, 40)
        oled.show()

        x_val = input_unit.read_joy_x()
        y_val = input_unit.read_joy_y()

        # 左右移動游標
        if x_val < JOY_LOW:
            index = (index - 1) % 3
            time.sleep(0.2)
        elif x_val > JOY_HIGH:
            index = (index + 1) % 3
            time.sleep(0.2)

        # 上下調整數字
        if y_val < JOY_LOW:
            digits[index] = (digits[index] + 1) % 10
            time.sleep(0.2)
        elif y_val > JOY_HIGH:
            digits[index] = (digits[index] - 1 + 10) % 10
            time.sleep(0.2)

        # 確認設定
        if input_unit.is_enter_pressed():
            while input_unit.is_enter_pressed(): time.sleep(0.01)
            break
    
    # 計算出 P1 設定的目標數字
    target = int("".join(str(d) for d in digits))
    
    # 提示交換玩家
    oled.fill(0)
    oled.text("Pass to P2", 20, 30)
    oled.show()
    time.sleep(2)

    # --- Phase 2: 玩家 2 猜數字 (同單人邏輯) ---
    low = 0
    high = 1000 # 3位數最大 999，所以上限是 1000
    count = 0
    guess = 500

    while True:
        oled.fill(0)
        oled.text("P2: Guess", 0, 0)
        oled.text(f"Range: {low}-{high}", 0, 15)
        oled.text(f"> {guess} <", 30, 40)
        oled.show()

        y_val = input_unit.read_joy_y()

        # 搖桿控制數字
        if y_val < JOY_LOW:
            if guess < high - 1:
                guess += 1
                if high - low > 100: time.sleep(0.05) # 加速
                else: time.sleep(0.15)
        elif y_val > JOY_HIGH:
            if guess > low + 1:
                guess -= 1
                if high - low > 100: time.sleep(0.05)
                else: time.sleep(0.15)

        # 確認
        if input_unit.is_enter_pressed():
            while input_unit.is_enter_pressed(): time.sleep(0.01)
            count += 1
            
            if guess == target:
                oled.fill(0)
                oled.text("P2 Wins!", 30, 20)
                oled.text(f"Tries: {count}", 30, 40)
                oled.show()
                time.sleep(3)
                return
            elif guess < target:
                low = guess
                guess = (low + high) // 2
                oled.fill(0)
                oled.text("Too Low!", 30, 30)
                oled.show()
                time.sleep(1)
            else:
                high = guess
                guess = (low + high) // 2
                oled.fill(0)
                oled.text("Too High!", 30, 30)
                oled.show()
                time.sleep(1)


# =====================================================
# 包裝接口：傳入 display 和 input
# =====================================================
def start_guess_easy(display_unit, input_unit):
    guess_number_game(1, 50, "best_easy.txt", display_unit, input_unit)

def start_guess_normal(display_unit, input_unit):
    guess_number_game(1, 100, "best_normal.txt", display_unit, input_unit)

def start_guess_hard(display_unit, input_unit):
    guess_number_game(1, 1000, "best_hard.txt", display_unit, input_unit)