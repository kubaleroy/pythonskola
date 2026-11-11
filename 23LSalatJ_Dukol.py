def inp(msg ,type: str, pr=None, repeating=False):
    type = type.lower().strip()
    num = input(msg)
    try:
        if type == "int":
            x = int(num)
            return x
        elif type == "float":
            x = float(num)
            return x
        elif type == "n":
            h = int(num)
            if h<=0: raise
            return h
        elif type == "dd":
            h = int(num)
            if h not in range(1,8,1): raise
            return h
        elif type == "pf":
            h = float(num)
            if h<0: raise
            return h
        else:
            raise Exception("invaltype")
    except Exception as e:
        print(f"Chyba: {e}")
        if e.args[0] == "invaltype":
            raise ValueError(f"Invald type {type}")
        if pr is not None:
            print(pr)
        if repeating:
            return inp(msg, type, pr, repeating)
        return False
#===================================================================================================================================
def uloha1():    
    pocet = inp("Zadej pocet polozek\n>>", "n", "Zadej cele cislo", True)
    k = []
    for i in range(pocet):
        k.append(inp(f"Zadej {i+1}. polozku\n>>", "pf", "Zadej nezapornou cenu", True))
    mezisoucet = sum(k)
    s = 0
    if mezisoucet > 5000:
        s = 0.1
    elif mezisoucet > 2000:
        s = 0.05
    cps = mezisoucet * (1 - s)
    pdph = cps * (1+0.21)
    print(f"Mezisoucet: {mezisoucet} Kc\nSleva: {mezisoucet - cps} Kc\nCena po sleve bez DPH: {cps} Kc\nDPH: {pdph - cps} Kc\nCena s DPH: {pdph} Kc")
#===================================================================================================================================
def uloha2():
    prijem = inp("Zadej prijem\n>>", "pf", "Zadej nezaporny ciselny prijem", True)
    pp = inp("Zadej pocet vydajovych polozek\n>>", "n", "Zadej cele cislo", True)
    k = {}
    maxsingle = [0,0]
    for i in range(pp):
        kategorie = input(f"Zadej kategorii {i+1}. vydaje\n>>")
        x = inp(f"Zadej {i+1}. vydaj\n>>", "pf", "Zadej nezapornou cenu", True)
        k[kategorie] = x + k.get(kategorie, 0)
        if x > maxsingle[1]:
            maxsingle = [kategorie, x]
    cel = sum(k.values())
    m = max(k.values())
    mk = [key for key, value in k.items() if value == m][0]
    print(f"Celkove vydaje: {cel} Kc\nZustatek: {prijem - cel} Kc\nProcento prijmu spotrebovano: {100 * cel / prijem}%\nKategorie s nejvyssimi vydaji: {mk} ({m} Kc)\nNejvyssi samostatny vydaj: {maxsingle[1]} Kc ({maxsingle[0]})")
    s = "Rozpocet je v minusu!\nO:" if prijem < cel else "Zbyva:"
    print(f"{s} {prijem - cel} Kc")
uloha1()
uloha2()