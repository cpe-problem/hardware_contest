#ifndef USB_DESCRIPTORS_H_
#define USB_DESCRIPTORS_H_

#include "tusb.h"

// 定義 Report ID
// 當你有多個功能（例如滑鼠+鍵盤）時，用 ID 來區分
enum {
    REPORT_ID_MOUSE = 1,
    REPORT_ID_COUNT
};

#endif