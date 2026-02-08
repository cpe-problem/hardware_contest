#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

// 定義為 Device 模式
#define CFG_TUSB_RHPORT0_MODE     OPT_MODE_DEVICE
#define CFG_TUSB_OS               OPT_OS_NONE

// 啟用 HID 類別 (1 表示啟用一個 HID 介面)
#define CFG_TUD_HID               1

// HID 緩衝區大小
#define CFG_TUD_HID_EP_BUFSIZE    64

#endif