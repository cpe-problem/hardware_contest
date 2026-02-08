#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "bsp/board.h"
#include "tusb.h"
#include "MPU6050.h"

#ifndef REPORT_ID_MOUSE
#define REPORT_ID_MOUSE 1
#endif

// I2C 設定
#define I2C_PORT i2c0
#define SDA_PIN 4
#define SCL_PIN 5

// 調校參數
#define SENSITIVITY 600  // 數值愈大愈慢
#define DEADZONE 10      // 死區：校正後若數值小於此則忽略 (原本200太大，校正後可改小)

// 全域變數：用來存儲偏差值
int32_t offset_gx = 0;
int32_t offset_gy = 0;
int32_t offset_gz = 0;

void calibrate_mpu(MPU6050 &sensor) {
    int16_t gx, gy, gz;
    int32_t sum_gx = 0, sum_gy = 0, sum_gz = 0;
    const int sample_count = 500; // 取樣 500 次

    // 讓感測器穩定一下
    sleep_ms(100);

    for (int i = 0; i < sample_count; i++) {
        sensor.getGyro(gx, gy, gz);
        sum_gx += gx;
        sum_gy += gy;
        sum_gz += gz;
        sleep_ms(2); // 稍微間隔
        tud_task();  // 保持 USB 連線不中斷
    }

    // 計算平均偏差
    offset_gx = sum_gx / sample_count;
    offset_gy = sum_gy / sample_count;
    offset_gz = sum_gz / sample_count;
}

int main() {
    board_init();
    tusb_init();
    
    // 初始化 I2C
    i2c_init(I2C_PORT, 400 * 1000);
    gpio_set_function(SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(SDA_PIN);
    gpio_pull_up(SCL_PIN);

    MPU6050 sensor(I2C_PORT);
    sensor.init();

    // === 執行開機校正 (關鍵步驟) ===
    // 請在此時保持靜止！
    calibrate_mpu(sensor);

    int16_t raw_gx, raw_gy, raw_gz;
    int32_t real_gx, real_gy, real_gz; // 使用 int32 避免計算溢出

    while (true) {
        tud_task(); 

        if (tud_hid_ready()) {
            sensor.getGyro(raw_gx, raw_gy, raw_gz);

            // 1. 扣除偏差值 (校正)
            real_gx = raw_gx - offset_gx;
            real_gy = raw_gy - offset_gy;
            real_gz = raw_gz - offset_gz;

            int8_t mouse_x = 0;
            int8_t mouse_y = 0;

            // 2. 死區判斷 (過濾微小手抖)
            // Z軸對應 X 移動 (左右)，X軸對應 Y 移動 (上下) - 視安裝方向調整
            if (abs(real_gz) > DEADZONE) mouse_x = (int8_t)(real_gz / SENSITIVITY);
            if (abs(real_gx) > DEADZONE) mouse_y = (int8_t)(real_gx / SENSITIVITY);

            // 3. 只有當數值不為 0 時才發送
            if (mouse_x != 0 || mouse_y != 0) {
                tud_hid_mouse_report(REPORT_ID_MOUSE, 0x00, mouse_x, mouse_y, 0, 0);
            }
        }
        sleep_ms(10); 
    }
}

// TinyUSB 回調函式
void tud_hid_set_report_cb(uint8_t itf, uint8_t report_id, hid_report_type_t report_type, uint8_t const* buffer, uint16_t bufsize) {
    (void) itf; (void) report_id; (void) report_type; (void) buffer; (void) bufsize;
}

uint16_t tud_hid_get_report_cb(uint8_t itf, uint8_t report_id, hid_report_type_t report_type, uint8_t* buffer, uint16_t reqlen) {
    (void) itf; (void) report_id; (void) report_type; (void) buffer; (void) reqlen;
    return 0;
}