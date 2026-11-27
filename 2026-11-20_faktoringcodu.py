def isvalid(veky):
    platne = True
    for v in veky:
        if v < 0 or v > 120:
            platne = False
    if not platne:
        print("Neplatná data.")
        return

def cats(prumer):
    if prumer < 20:
        kategorie = "mladý tým"
    elif prumer < 40:
        kategorie = "smíšený tým"
    else:
        kategorie = "starší tým"
    return kategorie


def zpracuj_veky(veky):
    isvalid(veky)
    prumer = sum(veky) / len(veky)
    kategorie = cats(prumer)
    print(f"Průměrný věk: {prumer:.1f} let ({kategorie})")


zpracuj_veky([25, 30, 22, 45, 28])