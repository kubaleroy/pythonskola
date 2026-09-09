import math
DECIMALS = 7
def score(x):
    return abs((40000000+1/math.pi)/40000000*math.pi + math.tan(x) - x)*10**6
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