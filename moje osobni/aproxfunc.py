import math
DECIMALS = 7

def 

def aproximate(func, decimals):
    score = lambda x: abs(func(x)-x)
    running = ""
    for i in range(decimals):




running = "3."
for i in range(DECIMALS):
    runx = running
    best = running
    for j in range(100):   
        runx += str(j/10).replace(".", "")
        if score(float(runx)) <= score(float(best)):
            best = running + runx[-2:]
        runx = running
    running += best[-2]
print(f"best t = {running} score {score(float(running))}")
print(f"  x best = {-40000000/2/math.pi - 40000000/2/math.pi/math.cos(float(running))} cos {math.cos(float(running))}")