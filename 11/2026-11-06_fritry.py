import matplotlib.pyplot as plt
import math

def ft(constsx, constsy, prec=2000):
    xs = []
    ys = []
    if type(constsx) == str:
        constsx = constsx.split(" ")
    if type(constsy) == str:
        constsy = constsy.split(" ")
    for i in range(prec):
        x = 0
        y = 0
        for constx in constsx:
            x += constx*math.cos(-i/prec*2*math.pi)
        for consty in constsy:
            y += consty*math.cos(-i/prec*2*math.pi)
        xs.append(x)
        ys.append(y)
    return xs, ys
#
x , y = ft()