#zadani
m = [
    "..#......",
    "..#.####.",
    "..#.#....",
    "....#....",
    "....#....",
    "....#....",
    "#........",
]


def checkA(startP: list, map:list, size:int):
#checks subarea of map
    for i in range(size):
        if "#" in map[startP[1]+i][startP[0]:startP[0]+size]:
            return False
    return True


rm = "#".join(m) #reduced map
rme = rm.split("#") 
sizes = [len(x) for x in rme]
posss = [] #POSsibleSizeS
for x in set(sizes):
    ct = 0
    for y in sizes:
        if x == y:
            ct += 1
    if ct >= x:
        posss.append(x)
for i in range(len(posss)):
    size = posss[-1]-i
    for l in range(len(m)-size):
        if "."*size in m[l]:
            if checkA([m[l].index("."*size),l], m, size):
                print(size)
                exit()


    

    
    
