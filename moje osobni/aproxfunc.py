import math
DECIMALS = 4

def optimize(func, running, Ndotted):
    score = lambda x: abs(func(x)-x)
    NotDotted = Ndotted
    runx = running
    best = running
    for j in range(100):
                runx += str(j/10) if NotDotted else str(j/10).replace(".", "")
                best = best if best!="" else 9999999999999
                if score(float(runx)) <= score(float(best)):
                    best = runx
                runx = running
    return best

def cat(func, running, NotDotted):
    best = optimize(func, running, NotDotted)
    if best.endswith("9.9") or best.endswith("99"):
        running = running[:-1] + str(int(running[-1]) + 1)
        running = cat(func, running, NotDotted)
    elif best.endswith("0.0") or best.endswith("00"):
        running = running[:-1] + str(int(running[-1]) - 1)
        running = cat(func, running, NotDotted)
    else:
        running += best[-2]
    return running


def aproximate(func, decimals):
    score = lambda x: abs(func(x)-x)
    running = ""
    NotDotted = True
    for i in range(decimals):
        running = cat(func, running, NotDotted)

        
