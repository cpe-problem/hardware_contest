#ifndef MPU6050_H
#define MPU6050_H

#include "pico/stdlib.h"
#include "hardware/i2c.h"

class MPU6050 {
public:
    MPU6050(i2c_inst_t* i2c_inst, uint8_t addr = 0x68);
    void init();
    void getGyro(int16_t& gx, int16_t& gy, int16_t& gz);

private:
    i2c_inst_t* i2c;
    uint8_t address;
};

#endif