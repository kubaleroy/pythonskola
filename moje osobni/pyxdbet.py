import pytesseract as tes
from PIL import Image
import cv2, time, keyboard
import pyautogui as pyi
import numpy as np

DELAY = 0

def getcoords():
    return pyi.position()

def waitfor(key):
    while True:
        time.sleep(0.05)
        if keyboard.is_pressed(key):
            return

#waitfor("Space")
#print(getcoords())
grid = []

waitfor("space")    
img = pyi.screenshot(region=[getcoords()[0]-5,getcoords()[1]-5, getcoords()[0]+5, getcoords()[1]+5])
colors = img.getcolors()
colors = [color[1] for color in colors]
majorcolor = np.average(colors,0)







