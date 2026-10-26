import pyautogui, keyboard, time
time.sleep(5)
while True:
    if keyboard.is_pressed('l'):
        break
    pyautogui.click()
    time.sleep(1)