#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

// 針對 Pico 2 (RP2350) 的建議設定
#include "tusb_option.h"
#define CFG_TUSB_MCU                OPT_MCU_RP2350 // 若 SDK 較舊請保留 RP2040
#define CFG_TUSB_RHPORT0_MODE       OPT_MODE_DEVICE

// 啟動 HID 功能
#define CFG_TUD_ENABLED             1
#define CFG_TUD_HID                 1
#define CFG_TUD_HID_EP_BUFSIZE      64

#endif