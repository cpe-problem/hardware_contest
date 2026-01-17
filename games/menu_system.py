from menu_loader import load_menu
from InputUnit import InputUnit
from DisplayUnit import DisplayUnit
import time
from machine import Pin, PWM 

# -----------------------------------------------------
# Helper: Reset High Scores
# -----------------------------------------------------
def reset_high_scores():
    files = [
        "best_easy.txt", "best_normal.txt", "best_hard.txt",
        "best_tetris.txt", 
        "best_maze_easy.txt", "best_maze_normal.txt", "best_maze_hard.txt",
        "best_shooter.txt"
        # Removed PUBG
    ]
    for f in files:
        try:
            with open(f, "w") as fp:
                fp.write("") 
        except:
            pass

# -----------------------------------------------------
# 初始化
# -----------------------------------------------------
input_unit = InputUnit()
display = DisplayUnit()
menu_data = load_menu("menu.json")

stack = [(menu_data["title"], menu_data["items"], 0)]

JOY_HIGH = 50000 
JOY_LOW = 15000  

def get_current():
    title, items, cursor = stack[-1]
    names = list(items.keys())
    return title, items, names, cursor

# -----------------------------------------------------
# 主迴圈
# -----------------------------------------------------
while True:
    title, items, names, cursor = get_current()
    display.show_menu(title, names, cursor)

    y_val = input_unit.read_joy_y()
    x_val = input_unit.read_joy_x()

    # 上下移動
    if y_val < JOY_LOW: 
        cursor = (cursor - 1) % len(names)
        stack[-1] = (title, items, cursor)
        time.sleep(0.2) 
    elif y_val > JOY_HIGH:
        cursor = (cursor + 1) % len(names)
        stack[-1] = (title, items, cursor)
        time.sleep(0.2)

    # 左鍵返回
    if x_val < JOY_LOW and len(stack) > 1:
        stack.pop()
        time.sleep(0.3)

    # 確認按鈕
    if input_unit.is_enter_pressed():
        while input_unit.is_enter_pressed(): time.sleep(0.01)

        key = names[cursor]
        item = items[key]

        if item["type"] == "submenu":
            stack.append((key, item["items"], 0))
            time.sleep(0.2)

        elif item["type"] == "action":
            action = item.get("action", "")

            # === Tetris ===
            if action == "start_tetris":
                from game_tetris import start_tetris_game
                start_tetris_game(display, input_unit)

            # === Guess Number ===
            elif action == "guess_easy":
                from game2 import start_guess_easy
                start_guess_easy(display, input_unit)
            elif action == "guess_normal":
                from game2 import start_guess_normal
                start_guess_normal(display, input_unit)
            elif action == "guess_hard":
                from game2 import start_guess_hard
                start_guess_hard(display, input_unit)
            elif action == "guess_versus":
                from game2 import start_guess_versus
                start_guess_versus(display, input_unit)

            # === Maze ===
            elif action == "maze_easy":
                from maze import start_maze_game
                start_maze_game(display, input_unit, "easy")
            elif action == "maze_normal":
                from maze import start_maze_game
                start_maze_game(display, input_unit, "normal")
            elif action == "maze_hard":
                from maze import start_maze_game
                start_maze_game(display, input_unit, "hard")

            # === Shooter ===
            elif action == "start_shooter":
                from game_shooter import start_shooter_game
                start_shooter_game(display, input_unit)

            # === Table Tennis ===
            elif action == "start_table_tennis":
                from game3_pingpong import start_table_tennis
                start_table_tennis(display, input_unit)

            elif action == "back_to_main":
                while len(stack) > 1:
                    stack.pop()
                time.sleep(0.2)

            # === High Scores (三頁顯示) ===
            elif action == "show_high_scores":
                from game2 import load_best
                
                # 讀取分數
                e = load_best("best_easy.txt")
                n = load_best("best_normal.txt")
                h = load_best("best_hard.txt")
                tt = load_best("best_tetris.txt")
                
                mz_e = load_best("best_maze_easy.txt")
                mz_n = load_best("best_maze_normal.txt")
                mz_h = load_best("best_maze_hard.txt")
                
                sh = load_best("best_shooter.txt")
                # Removed PUBG load

                # --- Page 1: Guess & Tetris ---
                display.oled.fill(0)
                display.oled.text("Scores (1/3)", 20, 0)
                display.oled.text(f"G-Easy: {e if e else '-'}", 0, 15)
                display.oled.text(f"G-Norm: {n if n else '-'}", 0, 25)
                display.oled.text(f"G-Hard: {h if h else '-'}", 0, 35)
                display.oled.text(f"Tetris: {tt if tt else '-'}", 0, 45) 
                
                display.oled.text(">> Next", 70, 55)
                display.oled.show()
                
                time.sleep(0.5)
                while not input_unit.is_enter_pressed(): pass
                while input_unit.is_enter_pressed(): pass 
                
                # --- Page 2: Maze ---
                display.oled.fill(0)
                display.oled.text("Scores (2/3)", 20, 0)
                display.oled.text(f"Mz-E: {mz_e}s" if mz_e else "Mz-E: -", 0, 20)
                display.oled.text(f"Mz-N: {mz_n}s" if mz_n else "Mz-N: -", 0, 32)
                display.oled.text(f"Mz-H: {mz_h}s" if mz_h else "Mz-H: -", 0, 44)
                
                display.oled.text(">> Next", 70, 55)
                display.oled.show()

                time.sleep(0.5)
                while not input_unit.is_enter_pressed(): pass
                while input_unit.is_enter_pressed(): pass

                # --- Page 3: Shooter ---
                display.oled.fill(0)
                display.oled.text("Scores (3/3)", 20, 0)
                
                display.oled.text(f"Shoot: {sh}" if sh else "Shoot: -", 0, 20)
                # Removed PUBG display
                
                display.oled.text(">> Exit", 70, 55)
                display.oled.show()

                time.sleep(0.5)
                while not input_unit.is_enter_pressed(): pass
                while input_unit.is_enter_pressed(): pass

            # === About ===
            elif action == "show_about":
                buzzer = PWM(Pin(20))
                notes = [523, 659, 784, 1046] 
                for note in notes:
                    buzzer.freq(note)
                    buzzer.duty_u16(32768)
                    time.sleep(0.1)
                time.sleep(0.3)
                buzzer.duty_u16(0)

                credits = [
                    "--- ABOUT ---",
                    "Triple-A Game",
                    "",
                    "Games:",
                    "Tetris",
                    "Guess Number",
                    "Maze Runner",
                    "Space Shooter",
                    "Table Tennis",
                    "",
                    "Created By:",
                    "Group 9",
                    "",
                    "--- END ---"
                ]

                y_scroll = 64 
                while True:
                    if input_unit.is_enter_pressed():
                        while input_unit.is_enter_pressed(): time.sleep(0.01)
                        break
                    display.oled.fill(0)
                    for i, line in enumerate(credits):
                        line_y = y_scroll + (i * 10) 
                        if -10 < line_y < 64:
                            x_pos = (128 - len(line) * 8) // 2
                            display.oled.text(line, int(x_pos), int(line_y))
                    display.oled.show()
                    y_scroll -= 1 
                    if y_scroll < -(len(credits) * 10):
                        y_scroll = 64
                    time.sleep(0.05) 

        elif item["type"] == "choice":
            options = item["options"]
            current_idx = 0
            if item["default"] in options:
                current_idx = options.index(item["default"])
            display.show_message(f"{key}: {item['default']}")
            time.sleep(0.3) 
            while True:
                display.show_message(f"{key}: <{item['default']}>")
                jx = input_unit.read_joy_x()
                if jx < JOY_LOW:
                    current_idx = (current_idx - 1) % len(options)
                    item["default"] = options[current_idx]
                    time.sleep(0.2)
                elif jx > JOY_HIGH:
                    current_idx = (current_idx + 1) % len(options)
                    item["default"] = options[current_idx]
                    time.sleep(0.2)
                if input_unit.is_enter_pressed():
                    while input_unit.is_enter_pressed(): pass 
                    break

        elif item["type"] == "range":
            val = item["default"]
            display.show_message(f"{key}: {val}")
            time.sleep(0.3)
            while True:
                display.show_message(f"{key}: <{val}>")
                jx = input_unit.read_joy_x()
                if jx < JOY_LOW:
                    if val > item["min"]:
                        val -= item["step"]
                        item["default"] = val
                    time.sleep(0.1) 
                elif jx > JOY_HIGH:
                    if val < item["max"]:
                        val += item["step"]
                        item["default"] = val
                    time.sleep(0.1)
                if input_unit.is_enter_pressed():
                    while input_unit.is_enter_pressed(): pass
                    break
    time.sleep(0.05)