import numpy as np
from random import randint as rand
import random
import argparse
SIZE = 20
COUNT = 20
RUNS = 20
ITERATIONS = 20

def nahodna_mapa(m, n, pravdepodobnost_o=0.05, pravdepodobnost_x=0.03, seed=None):
    rnd = random.Random(seed)
    mapa = []
    for _ in range(m):
        radek = []
        for _ in range(n):
            r = rnd.random()
            if r < pravdepodobnost_o:
                radek.append("o")
            elif r < pravdepodobnost_o + pravdepodobnost_x:
                radek.append("x")
            else:
                radek.append(".")
        mapa.append("".join(radek))
    return mapa

def vary(M :list, chance = 0.05):
    for i in range(len(M)):
        for j in range(len(M[i])):
            if rand(0,int(1/chance/2))==0:
                M[i][j] += 1
            if rand(0,int(1/chance/2))==0:
                M[i][j] -= 1
    return M

def sc(M,m):
    dot = np.dot(M,m)
    sc = np.linalg.det(dot)




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s","--size", default=20)
    parser.add_argument("-r","--runs", default=20)
    parser.add_argument("-c","--count", default=20)
    parser.add_argument("-i","--iterations", default=20)

    SIZE = int(vars(parser.parse_args())["size"])
    RUNS = int(vars(parser.parse_args())["runs"])
    COUNT = int(vars(parser.parse_args())["count"])
    ITERATIONS = int(vars(parser.parse_args())["iterations"])


    ms = [[0]*SIZE for _ in range(SIZE)]


    
