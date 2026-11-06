import matplotlib.pyplot as plt
import math
def spiral(pocetbodu, otocky=3):
    coords = [[],[]]
    for i in range(pocetbodu):
        angle = i/pocetbodu*otocky*2*math.pi
        r = i/pocetbodu
        coords[0].append(r*math.cos(angle))
        coords[1].append(r*math.sin(angle))
    return coords[0], coords[1]

def xx(freq1, freq2, prec, normal=False):
    x = []
    y = []
    for i in range(prec):
        x.append(math.cos(i*freq1/prec*2*math.pi))
        y.append(math.sin(i*freq2/prec*2*math.pi))
    return x,y

numrange = 5
coeff = 0.5
fig, axes = plt.subplots(numrange, numrange, figsize=(10, 10))
for j in range(numrange*numrange):
    x,y = xx((j%numrange+1)*coeff,(j//numrange+1)*coeff,2000)
    axes[j%numrange][j//numrange].scatter(x,y, s=1)
    axes[j%numrange][j//numrange].axis("equal")
plt.show()
 

