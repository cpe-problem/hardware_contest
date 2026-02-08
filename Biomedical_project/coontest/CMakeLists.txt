cmake_minimum_required(VERSION 3.13)
set(PICO_SDK_FETCH_FROM_GIT ON)
set(PICO_BOARD pico2_w)
# 引入 Pico SDK 設定檔
include(pico_sdk_import.cmake)

project(coontest C CXX ASM)

# ==========================================
# 建議加入：指定 C++ 標準
# 避免使用較舊的編譯器預設值導致語法錯誤
# ==========================================
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# 初始化 SDK
pico_sdk_init()

# ==========================================
# 定義執行檔與來源檔案
# 請確保資料夾內真的有這三個檔案：
# 1. coontest.cpp      (你的主程式)
# 2. MPU6050.cpp       (感測器實作)
# 3. usb_descriptors.c (USB 描述符)
# ==========================================
add_executable(coontest 
    coontest.cpp 
    MPU6050.cpp 
    usb_descriptors.c
)

# ==========================================
# 啟用 USB 輸出 (讓電腦識別為 USB 裝置)
# 禁用 UART (除非你有接 Serial 線除錯)
# ==========================================
pico_enable_stdio_usb(coontest 1)
pico_enable_stdio_uart(coontest 0)

# ==========================================
# 連結必要的庫
# tinyusb_device: 核心 USB 功能
# tinyusb_board:  板級 USB 定義
# hardware_i2c:   MPU6050 通訊用
# ==========================================
target_link_libraries(coontest 
    pico_stdlib 
    hardware_i2c 
    tinyusb_device 
    tinyusb_board
)

# 包含當前目錄 (讓編譯器找得到 tusb_config.h 和 MPU6050.h)
target_include_directories(coontest PRIVATE ${CMAKE_CURRENT_LIST_DIR})

# 生成 .uf2 檔案
pico_add_extra_outputs(coontest)