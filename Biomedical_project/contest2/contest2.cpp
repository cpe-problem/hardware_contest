#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "tusb.h"
#include "usb_descriptors.h"

#define ADDR 0x68
float sensitivity = 20.0f; // 數值越大移動越慢

void mpu6050_init() {
    uint8_t buf[] = {0x6B, 0x00};
    i2c_write_blocking(i2c_default, ADDR, buf, 2, false);
}

void send_mouse_report(int8_t x, int8_t y) {
    if (tud_hid_ready()) {
        tud_hid_mouse_report(REPORT_ID_MOUSE, 0, x, y, 0, 0);
    }
}

int main() {
    stdio_init_all();
    tusb_init();
    i2c_init(i2c_default, 400 * 1000);
    gpio_set_function(4, GPIO_FUNC_I2C); // SDA
    gpio_set_function(5, GPIO_FUNC_I2C); // SCL
    gpio_pull_up(4);
    gpio_pull_up(5);
    
    mpu6050_init();

    while (1) {
        tud_task(); // 必須不斷呼叫以維持 USB 連線

        uint8_t reg = 0x43;
        uint8_t data[6];
        i2c_write_blocking(i2c_default, ADDR, &reg, 1, true);
        i2c_read_blocking(i2c_default, ADDR, data, 6, false);

        int16_t gyro_x = (data[0] << 8) | data[1];
        int16_t gyro_z = (data[4] << 8) | data[5];

        // 簡單計算移動量
        int8_t move_x = (int8_t)(-gyro_z / 500);
        int8_t move_y = (int8_t)(-gyro_x / 500);

        send_mouse_report(move_x, move_y);
        sleep_ms(10);
    }
}