#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"

#define UART_ID uart0
#define BAUD_RATE 256000
#define UART_TX_PIN 0
#define UART_RX_PIN 1

int main() {
    stdio_init_all();

    // 初始化 UART 並設定引腳
    uart_init(UART_ID, BAUD_RATE);
    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);

    printf("LD2450 C++ SDK 測試開始...\n");

    uint8_t buffer[30]; // LD2450 數據幀長度約為 30 字節
    
    while (true) {
        if (uart_is_readable(UART_ID)) {
            // 讀取頭部幀 (AA FF 03 00)
            uint8_t head = uart_getc(UART_ID);
            if (head == 0xAA) {
                buffer[0] = head;
                for (int i = 1; i < 30; i++) {
                    buffer[i] = uart_getc(UART_ID);
                }
                
                // 簡單解析第一個目標的距離 (Offset 4, 5 為 X, Offset 6, 7 為 Y)
                // 具體數值需根據 LD2450 手冊做位元運算
                int16_t target1_x = (int16_t)(buffer[5] << 8 | buffer[4]);
                int16_t target1_y = (int16_t)(buffer[7] << 8 | buffer[6]);
                
                printf("目標 1 座標: X=%d mm, Y=%d mm\n", target1_x, target1_y);
            }
        }
    }
}