import machine
import time

# Pico W / 2 W 的板載 LED 通常叫 "LED"
led = machine.Pin("LED", machine.Pin.OUT)

while True:
    led.toggle()  # 切換開關
    print("Blinking...")
    time.sleep(0.5)