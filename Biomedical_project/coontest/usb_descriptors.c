#include "tusb.h"
#include <string.h> 

#define REPORT_ID_MOUSE 1

// 【修正】手動定義 HID_REPORT_ID，防止找不到定義
#ifndef HID_REPORT_ID
#define HID_REPORT_ID(x)  0x85, x
#endif

// 裝置描述符 (保持不變)
tusb_desc_device_t const desc_device = {
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB             = 0x0200,
    .bDeviceClass       = 0x00,
    .bDeviceSubClass    = 0x00,
    .bDeviceProtocol    = 0x00,
    .bMaxPacketSize0    = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor           = 0xcafe, 
    .idProduct          = 0x0001, 
    .bcdDevice          = 0x0100,
    .iManufacturer      = 0x01,
    .iProduct           = 0x02,
    .iSerialNumber      = 0x03,
    .bNumConfigurations = 0x01
};

uint8_t const * tud_descriptor_device_cb(void) {
    return (uint8_t const *) &desc_device;
}

// 【修正】HID 報告描述符
uint8_t const desc_hid_report[] = {
    // 使用上面手動定義的巨集，解決 "called object is not a function" 錯誤
    TUD_HID_REPORT_DESC_MOUSE( HID_REPORT_ID(REPORT_ID_MOUSE) )
};

uint8_t const * tud_hid_descriptor_report_cb(uint8_t itf) {
    (void) itf; 
    return desc_hid_report;
}

// 設定描述符
enum {
    ITF_NUM_HID,
    ITF_NUM_TOTAL
};

#define CONFIG_TOTAL_LEN  (TUD_CONFIG_DESC_LEN + TUD_HID_DESC_LEN)

uint8_t const desc_configuration[] = {
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP, 100),
    TUD_HID_DESCRIPTOR(ITF_NUM_HID, 0, HID_ITF_PROTOCOL_MOUSE, sizeof(desc_hid_report), 0x81, CFG_TUD_HID_EP_BUFSIZE, 10)
};

uint8_t const * tud_descriptor_configuration_cb(uint8_t index) {
    (void) index; 
    return desc_configuration;
}

// 字串描述符
char const* string_desc_arr [] = {
    (const char[]) { 0x09, 0x04 }, // 0: 語言 ID
    "Raspberry Pi",                // 1: 廠商
    "Pico Air Mouse",              // 2: 產品名稱
    "123456"                       // 3: 序號
};

static uint16_t _desc_str[32];

uint16_t const* tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void) langid;
    uint8_t chr_count;

    if ( index == 0 ) {
        memcpy(&_desc_str[1], string_desc_arr[0], 2);
        chr_count = 1;
    } else {
        if ( !(index < sizeof(string_desc_arr)/sizeof(string_desc_arr[0])) ) return NULL;

        const char* str = string_desc_arr[index];
        chr_count = (uint8_t) strlen(str);
        if ( chr_count > 31 ) chr_count = 31;

        for(uint8_t i=0; i<chr_count; i++) {
            _desc_str[1+i] = str[i];
        }
    }

    _desc_str[0] = (TUSB_DESC_STRING << 8 ) | (2*chr_count + 2);

    return _desc_str;
}