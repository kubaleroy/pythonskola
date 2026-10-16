import math
b1 = list(map(float, input("x1, y1 = ").strip().split(",")))
b2 = list(map(float, input("x2, y2 = ").strip().split(",")))
print(f"vzdalenost {math.sqrt((b1[0]-b2[0])**2+(b1[1]-b2[1])**2):.3f}")