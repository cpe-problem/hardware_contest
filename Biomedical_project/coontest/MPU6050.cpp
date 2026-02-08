#include <stdint.h>          // 必須加入，定義了 uint8_t, int16_t
#include "MPU6050.h"
#include "hardware/i2c.h"    // 確保包含 i2c 相關函式

MPU6050::MPU6050(i2c_inst_t* i2c_inst, uint8_t addr) : i2c(i2c_inst), address(addr) {}

void MPU6050::init() {
    uint8_t data[] = {0x6B, 0x00}; // 喚醒 MPU6050
    i2c_write_blocking(i2c, address, data, 2, false);
}

void MPU6050::getGyro(int16_t& gx, int16_t& gy, int16_t& gz) {
    uint8_t reg = 0x43;
    uint8_t buffer[6];
    i2c_write_blocking(i2c, address, &reg, 1, true);
    i2c_read_blocking(i2c, address, buffer, 6, false);

    gx = (int16_t)((buffer[0] << 8) | buffer[1]);
    gy = (int16_t)((buffer[2] << 8) | buffer[3]);
    gz = (int16_t)((buffer[4] << 8) | buffer[5]);
}