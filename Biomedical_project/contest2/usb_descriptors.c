#include <stdint.h>
#include <string.h>
#include "tusb.h"
#include "usb_descriptors.h"

/* -------------------------------------------------------------------- */
/* Device Descriptor (設備描述符) */
/* -------------------------------------------------------------------- */
tusb_desc_device_t const desc_device = {
    .bLength            = 18,
    .bDescriptorType    = 1, // TUSB_DESC_DEVICE
    .bcdUSB             = 0x0200,
    .bDeviceClass       = 0x00,
    .bDeviceSubClass    = 0x00,
    .bDeviceProtocol    = 0x00,
    .bMaxPacketSize0    = 64,
    .idVendor           = 0x2E8A, 
    .idProduct          = 0x000A, 
    .bcdDevice          = 0x0100,
    .iManufacturer      = 0x01,
    .iProduct           = 0x02,
    .iSerialNumber      = 0x03,
    .bNumConfigurations = 0x01
};

uint8_t const * tud_descriptor_device_cb(void) {
    return (uint8_t const *) &desc_device;
}

/* -------------------------------------------------------------------- */
/* HID Report Descriptor (滑鼠報表描述符) - 使用手動展開版，徹底解決紅字 */
/* -------------------------------------------------------------------- */
// 修正版：移除所有可能干擾編譯器的註解括號
uint8_t const desc_hid_report[] = {
    0x05, 0x01,                    // Usage Page (Generic Desktop)
    0x09, 0x02,                    // Usage (Mouse)
    0xa1, 0x01,                    // Collection (Application)
    0x85, REPORT_ID_MOUSE,         // Report ID
    0x09, 0x01,                    // Usage (Pointer)
    0xa1, 0x00,                    // Collection (Physical)
    0x05, 0x09,                    //   Usage Page (Button)
    0x19, 0x01,                    //   Usage Minimum (Button 1)
    0x29, 0x03,                    //   Usage Maximum (Button 3)
    0x15, 0x00,                    //   Logical Minimum (0)
    0x25, 0x01,                    //   Logical Maximum (1)
    0x95, 0x03,                    //   Report Count (3)
    0x75, 0x01,                    //   Report Size (1)
    0x81, 0x02,                    //   Input (Data,Var,Abs)
    0x95, 0x01,                    //   Report Count (1)
    0x75, 0x05,                    //   Report Size (5)
    0x81, 0x03,                    //   Input (Cnst,Var,Abs)
    0x05, 0x01,                    //   Usage Page (Generic Desktop)
    0x09, 0x30,                    //   Usage (X)
    0x09, 0x31,                    //   Usage (Y)
    0x15, 0x81,                    //   Logical Minimum (-127)
    0x25, 0x7f,                    //   Logical Maximum (127)
    0x75, 0x08,                    //   Report Size (8)
    0x95, 0x02,                    //   Report Count (2)
    0x81, 0x06,                    //   Input (Data,Var,Rel)
    0xc0,                          // End Collection
    0xc0                           // End Collection
};

uint8_t const * tud_hid_descriptor_report_cb(uint8_t instance) {
    (void) instance;
    return desc_hid_report;
}

/* -------------------------------------------------------------------- */
/* Configuration Descriptor (配置描述符) - 使用明確數值避免 sizeof 報錯 */
/* -------------------------------------------------------------------- */
// 將原本的 desc_configuration 改寫為靜態數值版
uint8_t const desc_configuration[] = {
    // 總長度 34 bytes (0x22)
    0x09, 0x02, 0x22, 0x00, 0x01, 0x01, 0x00, 0xA0, 0x32,
    // Interface Descriptor
    0x09, 0x04, 0x00, 0x00, 0x01, 0x03, 0x01, 0x02, 0x00,
    // HID Descriptor
    0x09, 0x21, 0x11, 0x01, 0x00, 0x01, 0x22, 0x12, 0x00,
    // Endpoint Descriptor
    0x07, 0x05, 0x81, 0x03, 0x08, 0x00, 0x0A
};

uint8_t const * tud_descriptor_configuration_cb(uint8_t index) {
    (void) index;
    return desc_configuration;
}

/* -------------------------------------------------------------------- */
/* String Descriptors (字串描述符) */
/* -------------------------------------------------------------------- */
char const* string_desc_arr [] = {
    (const char[]) { 0x09, 0x04 }, 
    "Raspberry Pi",                
    "Pico 2 Air Mouse",            
    "123456",                      
};

static uint16_t _desc_str[32];

uint16_t const* tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void) langid;
    uint8_t chr_count;

    if ( index == 0 ) {
        memcpy(&_desc_str[1], string_desc_arr[0], 2);
        chr_count = 1;
    } else {
        if ( !(index < 4) ) return NULL;
        const char* str = string_desc_arr[index];
        chr_count = (uint8_t) strlen(str);
        if ( chr_count > 31 ) chr_count = 31;
        for(uint8_t i=0; i<chr_count; i++) _desc_str[1+i] = (uint16_t)str[i];
    }

    _desc_str[0] = (uint16_t)((3 << 8) | (2 * chr_count + 2));
    return _desc_str;
}