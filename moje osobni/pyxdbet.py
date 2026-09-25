import pytesseract as tes
from PIL import Image
import cv2, time, keyboard
import pyautogui as pyi
import numpy as np

DELAY = 0
speed = 0

def getcoords():
    return pyi.position()

def waitfor(key):
    while True:
        time.sleep(0.05)
        if keyboard.is_pressed(key):
            return

def getmajorcolor(region):
    img = pyi.screenshot(region=region)
    colors = img.getcolors()
    colors = [color[1] for color in colors]
    return np.average(colors,0)


#waitfor("Space")
#print(getcoords())
grid = []
waitfor("space")    
reg = [getcoords()[0]-5,getcoords()[1]-5, getcoords()[0]+5, getcoords()[1]+5]
print(getmajorcolor(reg))








