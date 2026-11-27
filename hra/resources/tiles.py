from PIL import Image
from random import randint


res = [416,275]
#tiled 3x2
"""
416 = 2xgap + 3xtile
275 = gap + 2x tile
tile = 134
"""
tile = 128
gap = res[1]-2*tile-3
vgap = gap+3
tiles = []
with Image.open("tiles.jpg") as im:
    for i in range(0,6):
        if i ==1:pass
        if i == 3: pass
        tiles.append(im.crop([(tile+gap)*(i%3),(tile+vgap)*(i%2),(tile+gap)*(i%3)+tile,(tile+vgap)*(i%2)+tile]))
    im.close()
def getRandomFloorTile():
    return tiles[randint(0,5)].rotate(90*randint(0,3))