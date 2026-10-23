def qsort(inlist):
    if inlist == []: 
        return []
    else:
        pivot = inlist[0]
        lesser = qsort([x for x in inlist[1:] if x[0] > pivot[0]])
        greater = qsort([x for x in inlist[1:] if x[0] <= pivot[0]])
        return lesser + [pivot] + greater


print(qsort([[5,2],[1,8],[6,4]]))