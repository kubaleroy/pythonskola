import matplotlib.pyplot as plt
import math
def xx(amps1, amps2, prec, normal=False):
    x = []
    y = []
    for i in range(prec + 1):  
        t = i/prec*2*math.pi
        x.append(sum([amps1[k-1][0]*math.cos(k*t) + amps1[k-1][1]*math.sin(k*t)
                      for k in range(1, len(amps1)+1)]))
        y.append(sum([amps2[k-1][0]*math.cos(k*t) + amps2[k-1][1]*math.sin(k*t)
                      for k in range(1, len(amps2)+1)]))
    return x, y
#circle: [[1,0]], [[0,1]]
#heart: [[0,12],[0,0],[0,-4]], [[13,0],[-5,0],[-2,0],[-1,0]]
#snowflake [[1,0]] + [[0,0]]*5 + [[0.5,0]] + [[0,0]]*9 + [[0.3,0]], [[0,1]] + [[0,0]]*5 + [[0,0.5]] + [[0,0]]*9 + [[0,-0.3]]
#mandala [[1,0], [0,0], [0,0], [0.4,0]]  + [[0,0]]*6 + [[0.15,0], [0,0], [0,0], [0.08,0]], [[0,1], [0,0], [0,0], [0,-0.4]] + [[0,0]]*6 + [[0,0.15], [0,0], [0,0], [0,-0.08]]

x, y = xx([[1,0]] + [[0,0]]*5 + [[0.5,0]] + [[0,0]]*9 + [[0.3,0]], [[0,1]] + [[0,0]]*5 + [[0,0.5]] + [[0,0]]*9 + [[0,-0.3]], 10000)
plt.scatter(x, y, s=1)
plt.axis("equal")
plt.title("Křivka z Fourierovy řady")
plt.show()
 

