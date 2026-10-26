import math
DECIMALS = 4

def optimize(func, running, Ndotted):
    score = lambda x: abs(func(x)-x)
    NotDotted = Ndotted
    runx = running
    best = running
    for j in range(100):
        runx += str(j/10) if NotDotted else str(j/10).replace(".", "")
        best = best if best!="" else 0
        if score(float(runx)) <= score(float(best)):
            best = runx
        runx = running
    return best

def MEMundo(running, down):
    if down:
        running = running[:-1] + str(float(running[-1]) + 1) if running[-1] != "." else running[:-2] + str(float(running[-2]) + 1) + "."
    else:
        running = running[:-1] + str(float(running[-1]) - 1) if running[-1] != "." else running[:-2] + str(float(running[-2]) - 1) + "."
    return running


def appendIX(running, best, NotDotted):
    if "." in best and NotDotted:
        NotDotted = False
        running += best[-3] + "."
    elif "." in best:
        running += best[-3]
    else:
        running += best[-2]
    print(f"Running: {running} NotDotted: {NotDotted}")
    return running, NotDotted


def cat(func, running, NotDotted):
    score = lambda x: abs(func(x)-x)
    best = optimize(func, running, NotDotted)
    print(f"CATTED Best: {best} running: {running} NotDotted: {NotDotted} ")
    if best.endswith("9.9") or best.endswith("99"):
        print(best, running, NotDotted)
        running = running[:-1] + str(float(running[-1]) + 1) if running[-1] != "." else running[:-2] + str(float(running[-2]) + 1) + "." 
        if score(float(appendIX(MEMundo(running, False), best, NotDotted)[0])) > score(float(appendIX(running, best, NotDotted)[0])):
            running = MEMundo(running, False)
            return appendIX(running, best, NotDotted)
        running, NotDotted = cat(func, running, NotDotted)
    elif best.endswith("0.0") or best.endswith("00"):
        print(best, running, NotDotted)
        running = running[:-1] + str(float(running[-1]) - 1) if running[-1] != "." else running[:-2] + str(float(running[-2]) - 1) + "."
        if score(float(appendIX(MEMundo(running, True), best, NotDotted)[0])) > score(float(appendIX(running, best, NotDotted)[0])):
            running = MEMundo(running, True)
            return appendIX(running, best, NotDotted)
        running, NotDotted = cat(func, running, NotDotted)
    else:
        print(f"Best: {best} score: {abs(func(float(best))-float(best)):.5f}")
        running, NotDotted = appendIX(running, best, NotDotted)
    return running, NotDotted


def aproximate(func, decimals):
    score = lambda x: abs(func(x)-x)
    running = ""
    NotDotted = True
    for i in range(decimals):
        running, NotDotted = cat(func, running, NotDotted)
        #print(running)
       # print(f"ApproximationTEST of {func.__name__}: {running} score: {score(float(running)):.5f}")
    print(f"Approximation of {func.__name__}: {running} score: {score(float(running)):.{decimals+5}f}")
    return float(running)




l = aproximate(lambda x: (10/(math.e**x))**2, 5)
print(f"Approximation: {l} score: {(10/(math.e**l))**2:.5f}")