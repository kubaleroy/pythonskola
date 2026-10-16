import pyautogui as pyi
import keyboard
import time


speed = 0
acc = 98*3
dt = 0.001
last = None
lastdt = None
s = time.time_ns()
while not keyboard.is_pressed("alt"):
    s2 = time.time_ns()
    p = pyi.position()
    if (last is not None and lastdt is not None) and (int(last +speed*lastdt) != int(p[1])):
        speed = 0
        print("moved", last, p)
    speed += acc*(s2-s)/1000000
    pyi.moveTo((p[0], p[1]+speed*(s2-s)/1000000))
    last = p[1]
    lastdt = (s2-s)/1000000
    s = time.time_ns()