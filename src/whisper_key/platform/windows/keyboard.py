import pyautogui

pyautogui.FAILSAFE = True

def set_delay(delay: float):
    pyautogui.PAUSE = delay

def send_hotkey(*keys: str):
    pyautogui.hotkey(*keys)

def send_key(key: str):
    pyautogui.press(key)
