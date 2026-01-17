from machine import Pin, ADC
import time, urandom
from DisplayUnit import DisplayUnit

# ==============================================
# 永遠產生不重複的答案
# ==============================================
def generate_answer(digits, allow_repeat=False):
    numbers = list("0123456789")

    ans = ""
    for _ in range(digits):
        idx = urandom.getrandbits(16) % len(numbers)
        ans += numbers.pop(idx)
    return ans


# ==============================================
# 計算幾 A 幾 B
# ==============================================
def calc_ab(guess, answer):
    A = sum(guess[i] == answer[i] for i in range(len(answer)))
    B = sum(g in answer for g in guess) - A
    return A, B


# ==============================================
# 主遊戲
# ==============================================
def start_ab_game(digits=4, allow_repeat=False):
    display = DisplayUnit()

    # 永遠不重複，allow_repeat 無效
    answer = generate_answer(digits)

    knob = ADC(Pin(27))
    btn_add = Pin(16, Pin.IN, Pin.PULL_UP)
    btn_ok  = Pin(17, Pin.IN, Pin.PULL_UP)

    guess = ["0"] * digits
    index = 0

    segment = 65536 // digits

    while True:
        display.oled.fill(0)
        display.oled.text("A/B Game", 0, 0)
        display.oled.text("Guess:", 0, 20)
        display.oled.text("".join(guess), 60, 20)

        cursor_x = 60 + index * 6
        display.oled.text("^", cursor_x, 32)
        display.oled.show()

        adc = knob.read_u16()
        new_index = min(adc // segment, digits - 1)
        if new_index != index:
            index = new_index
            time.sleep(0.12)

        if btn_add.value() == 0:
            guess[index] = str((int(guess[index]) + 1) % 10)
            time.sleep(0.2)

        if btn_ok.value() == 0:
            g = "".join(guess)
            A, B = calc_ab(g, answer)

            display.oled.fill(0)
            display.oled.text(g, 0, 0)
            display.oled.text(f"{A}A{B}B", 0, 20)
            display.oled.show()
            time.sleep(1.2)

            if A == digits:
                display.oled.fill(0)
                display.oled.text("Correct!", 0, 25)
                display.oled.show()
                time.sleep(2)
                return
