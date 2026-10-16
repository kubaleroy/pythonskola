#help
def check(num, type:str, pr=None):
    type = type.lower().strip()
    try:
        if type == "int":
            int(num)
            return [True, int(num)]
        elif type == "float":
            float(num)
            return [True, float(num)]
        elif type == "positive":
            h = int(num)
            if h<=0:
                int("2.5")
            return [True, int(num)]
        elif type == "dd":
            h = int(num)
            if h not in range(1,8,1):
                int("2.5")
            return [True, int(num)]
        elif type == "pf":
            h = float(num)
            if h<0:
                int("2.5")
            return [True, float(num)]
    except:
        if pr is not None:
            print(pr)
        return False
#=========================================ULOHA 1=================================================================
def uloha1():
    pocet = check(input("Kolik se prodalo vstupenek: "), "positive", "Zadejte platny pocet vstupenek")
    while not pocet:
        pocet = check(input("Kolik se prodalo vstupenek: "), "positive", "Zadejte platny pocet vstupenek")
    pocet = pocet[1]
    veky = []
    #      <15,16-25,>25
    cats = [[],[],[]]
    while len(veky) < pocet:
        inp = check(input(f"Zadej {len(veky)+1}. vek: "), "positive", "Zadejte platny vek")
        if inp:
            inp = inp[1]
            veky.append(inp)
            if inp <= 15:
                cats[0].append(inp)
            elif inp <=25:
                cats[1].append(inp)
            else:
                cats[2].append(inp)
    print(f"ZDARMA: {len(cats[0])}\nZLEVNENE: {len(cats[1])}\nPLNE: {len(cats[2])}\nPRUMERNY_VEK: {sum(veky)/len(veky):.1f}")
    if len(cats[0])*2 > len(cats[1])+len(cats[2]):
        print("Pozor: hodne deti, zvazte rodinnou zonu.")
    print(f"NEJSTARSI: {max(veky)}\nNEJMLADSI: {min(veky)}")
#================================================ULOHA 2======================================================================
def uloha2():
    n = False
    while not n:
        n = check(input("Kolik dni: "), "dd", "Zadejte platny pocet dnu")
    n = n[1]
    t = []
    while len(t)<n:
        inp = check(input(f"Zadej trzby za {len(t)+1}. den: "), "pf", "Zadej platnou trzbu")
        if inp:
            inp = inp[1]
            t.append(inp)
    print(f"CELKEM: {sum(t)}\nPRUMER: {sum(t)/len(t):.2f}\nNEJLEPSI_DEN: {1+t.index(max(t))}")
    m = False
    while not m:
        m = check(input("Limit trzeb: "), "positive", "Zadejte platny limit trzeb")
    m = m[1]
    l = ""
    if m<sum(t):
        l = "prekroceno o "
    else:
        l = "chybi "
    print(f"LIMIT_INFO: {l}{abs(sum(t)-m)} Kc")
    p = sum(t)/len(t)
    c = 0
    for d in t:
        if d<p:
            c+=1
    print(f"POD_PRUMEREM: {c}")
#===============================================================================================================
uloha1()
uloha2()