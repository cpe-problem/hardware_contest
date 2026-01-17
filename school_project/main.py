from menu_loader import load_menu
from InputUnit import InputUnit
from DisplayUnit import DisplayUnit
from menu_system import MenuSystem

def main():
    # 讀取 JSON
    menu_data = load_menu("menu.json")

    # 建立輸入與顯示單元
    input_unit = InputUnit()
    display_unit = DisplayUnit()

    # 建立選單系統
    menu = MenuSystem(menu_data, input_unit, display_unit)

    # 進入主迴圈
    menu.run()

if __name__ == "__main__":
    main()
