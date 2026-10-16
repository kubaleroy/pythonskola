def checkA(startP: list, map:list, size:int):
#checks subarea of map
    for i in range(size):
        if "#" in map[startP[1]+i][startP[0]:startP[0]+size]:
            return False
    return True

m = [
    "..#......",
    "..#.####.",
    "..#.#....",
    "....#.#..",
    "....#....",
    "....#....",
    "#........",
]

for i in range(len(m)-3):
    for j in range(len(m[0])-3):
        if checkA([j,i], m,3):
            print("TRUE")
            exit()
print("nuhuh")