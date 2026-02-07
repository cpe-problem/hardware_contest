cmake_minimum_required(VERSION 3.13)

# 設定 C/C++ 標準
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# == VS Code Extension 自動配置區塊 ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# =================================

# 強制設定開發板為 Pico 2 W
set(PICO_BOARD pico2_w CACHE STRING "Board type")

# 匯入 Pico SDK
include(pico_sdk_import.cmake)

project(contest2 C CXX ASM)

# 初始化 SDK
pico_sdk_init()

# --------------------------------------------------------------------
# 執行檔配置：必須包含主程式與 USB 描述符檔案
# --------------------------------------------------------------------
add_executable(contest2 
    contest2.cpp 
    usb_descriptors.c
)

# --------------------------------------------------------------------
# 連結函式庫：整合 TinyUSB 核心與硬體驅動
# --------------------------------------------------------------------
target_link_libraries(contest2 
    pico_stdlib             # 標準庫
    tinyusb_device          # USB 設備模式支援
    tinyusb_board           # TinyUSB 板級支援
    hardware_i2c            # MPU6050 通訊支援
    # 其他你原本需要的硬體庫
    hardware_spi
    hardware_dma
    hardware_pio
    hardware_interp
    hardware_timer
    hardware_watchdog
    hardware_clocks
    pico_cyw43_arch_none
)

# --------------------------------------------------------------------
# 編譯定義：啟用 USB HID 功能
# --------------------------------------------------------------------
target_compile_definitions(contest2 PRIVATE
    PICO_USB_DEVICE_STACK=1 # 啟用 USB 設備堆疊
)

# --------------------------------------------------------------------
# 包含路徑：確保能找到 tusb_config.h
# --------------------------------------------------------------------
target_include_directories(contest2 PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
)

# 啟用 USB 輸出 (用於 Serial 偵錯)
pico_enable_stdio_usb(contest2 1)
pico_enable_stdio_uart(contest2 0)

# 產生額外的輸出口檔案 (如 .uf2)
pico_add_extra_outputs(contest2)