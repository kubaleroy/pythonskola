
"""
StavebPlocha — Pavilon na experimentálním území
Na kraji města se roky rozkládá Experimentální území — pozemek, který fakulta biologie používá ke sledování drobných živočichů a rostlin, jaké se ve městě jinde skoro nevidí. Část plochy je úplně obyčejná holá zem, na které se dá bez obav stavět. Tu a tam je ale skrytá malá ploška, kterou si oblíbil nějaký vzácný obyvatel — třeba hnízdo ještěrky nebo ostrůvek zvláštní byliny. Fakulta ji nechce zničit, ale zas tak úzkostlivá není: pokud přes takové místo opravdu potřebujete stavět, smíte ho na jednom místě přemostit — postavit nad ním na sloupech, aby zem pod stavbou zůstala nedotčená. Jsou tam ale i místa, na která sahat nesmíte vůbec — starý balvan, tůň, část poškozeného terénu — přes ty se nedá stavět ani je přemostit, těm se prostě musíte vyhnout.

Studentská katedra dostala za úkol na tohle území navrhnout nový pavilon pro terénní výzkum. Aby měl dost místa na dvě oddělené laboratoře a zároveň je spojoval jedinou chodbou (kvůli sdílenému vybavení a snazší kontrole), musí mít půdorys tvaru písmene H: dvě rovnoběžná křídla propojená jednou chodbou uprostřed.

Vaším úkolem je najít, kam pavilon ve tvaru H umístit, aby vyšel co největší — a napsat program, který to spočítá pro libovolnou mapu pozemku.

Pravidla
Pozemek je zaznamenaný jako obdélníková mřížka o M řádcích a N sloupcích. Každé políčko je jednoho ze tří typů:

. — volná plocha, na které lze stavět.
o — chráněné stanoviště (hnízdiště, vzácná rostlina...). Jedno takové políčko smíte „přemostit“ — stavět nad ním — ale jen jednou. Narazí-li stejná linie na druhé takové políčko, dál už pokračovat nemůže.
jakýkoli jiný znak — trvale nezastavitelná překážka (balvan, tůň, poškozený terén...). Přes ni stavět ani přemosťovat nelze vůbec — stavba se v tomto směru zastaví okamžitě.
Půdorys pavilonu má tvar písmene H: dvě rovnoběžná křídla o šířce jednoho políčka, spojená vodorovnou chodbou o výšce jednoho políčka. Volí se řádek chodby a dva sloupce (levé a pravé křídlo) tak, aby platilo:

obě křídla vedou od chodby stejně vysoko nahoru a stejně hluboko dolů (Musí vést aspoň jedno políčko nahoru a aspoň jedno políčko dolů. Skutečné H, ne tvar U nebo obrácené U/písmeno Π s jen jedním směrem. Křídla jsou vůči sobě symetrická; výška „nahoru“ a „dolů“ se ale mezi sebou shodovat nemusí.),
v každém ze tří přímých úseků (Obě křídla, chodb) platí výše popsané pravidlo o jednom přemostitelném políčku „o“.
Chodba může být libovolně dlouhá — délka roste s tím, jak daleko od sebe křídla zvolíš. Jediné omezení: mezi křídly musí zůstat aspoň jedno volné políčko chodby (křídla nesmí být bezprostředně vedle sebe).

Úkol: Najděte půdorys s největší možnou plochou (počtem políček).


Formát
Napiš funkci

def najdi_nejvetsi_plochu(mapa: list[str]) -> int:
    ...
mapa je seznam M řetězců, každý o délce N — přesně tak, jak vypadá pozemek (., o, nebo jiný znak).
funkce vrátí jedno celé číslo — obsah (počet políček) největší možné H-plochy. Pokud žádnou takovou budovu nelze postavit, vrať 0.

Ukázky — princip přemostění
Tři malé mapy (3 řádky × 9 sloupců) ukazují, jak se chová jedno přemostitelné políčko o oproti trvalé překážce. Ve všech třech je jediný použitelný (vnitřní) řádek řádek 2 — proto malý rozdíl v mapě rovnou ukáže rozdíl ve výsledku.

Příklad 1 — jedno o se dá přemostit, výsledek stejný jako na prázdné ploše:

.........
...o.....
.........
Výstup: 13

Příklad 2 — dvě o ve stejné linii: první se přemostí, na druhém se stavba zastaví:

.........
...o..o..
.........
Výstup: 10

Příklad 3 — trvalá překážka (x) se přemostit nedá vůbec:

.........
...x.....
.........
Výstup: 9

Hlavní ukázka
Mapa 7 × 11 s podélnou „zdí“ z trvalých překážek (sloupec 6), kterou lze přejít jen v jednom jediném řádku, kde je místo zdi chráněné stanoviště o (jediný můstek přes zeď):

.....x.....
.....x.....
.....x.....
.....o.....
.....x.....
.....x.....
.....x.....
Výstup: 23

Pro srovnání: kdyby byl i řádek s můstkem plná zeď (samé x, žádné o), maximum by kleslo na 17 — obě poloviny pozemku by pak nešlo vůbec propojit.

ef _test():
    priklad_1 = [
        ".........",
        "...o.....",
        ".........",
    ]
    assert najdi_nejvetsi_plochu(priklad_1) == 13, "Příklad 1 (jedno o, mělo by se přemostit)"

    priklad_2 = [
        ".........",
        "...o..o..",
        ".........",
    ]
    assert najdi_nejvetsi_plochu(priklad_2) == 10, "Příklad 2 (dvě o, jen první se přemostí)"

    priklad_3 = [
        ".........",
        "...x.....",
        ".........",
    ]
    assert najdi_nejvetsi_plochu(priklad_3) == 9, "Příklad 3 (x se nedá přemostit)"

    hlavni_ukazka = [
        ".....x.....",
        ".....x.....",
        ".....x.....",
        ".....o.....",
        ".....x.....",
        ".....x.....",
        ".....x.....",
    ]
    assert najdi_nejvetsi_plochu(hlavni_ukazka) == 23, "Hlavní ukázka (můstek přes zeď)"

    plna_zed = [
        ".....x.....",
        ".....x.....",
        ".....x.....",
        ".....x.....",
        ".....x.....",
        ".....x.....",
        ".....x.....",
    ]
    assert najdi_nejvetsi_plochu(plna_zed) == 17, "Plná zeď (bez můstku)"

    zadna_stavba = [
        "ooo",
        "ooo",
        "ooo",
    ]
    assert najdi_nejvetsi_plochu(zadna_stavba) == 0, "Samé chráněné plochy — nejde nic postavit"

    print("Všechny testy prošly! Gratuluji!")

_test()

import random
import time

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

velka_mapa = nahodna_mapa(80, 80, seed=42)
start = time.time()
vysledek = najdi_nejvetsi_plochu(velka_mapa)
konec = time.time()
print(f"Výsledek: {vysledek}, čas: {konec - start:.3f} s")
"""
#split areas, max possible, tests
PLOCHA = [#.->1,x->0,o->2
        ".....x.....",#11111011111
        ".....x.....",#11111011111
        ".....x.....",#11111011111
        ".....x.....",#11111011111
        ".....x.....",#11111011111
        ".....x.....",#11111011111
        ".....x.....",#11111011111
    ]
def rebrand(map):
    map = map.copy()
    i = 0
    for row in map:
        map[i] = map[i].replace(".", "1").replace("x", "0").replace("o", "2")
        i+=1

    return map


def check(rmap, indexs, proportions):
    m = 1
    for i in range(proportions[1]):
        m *= int(rmap[indexs[1]+i][indexs[0]])*int(rmap[indexs[1]+i][indexs[0]+proportions[0]-1])
        if m == 0:
            return 0
    for n in range(proportions[0]-2):
        m *= int(rmap[indexs[1]+int((proportions[1]-1)/2)][indexs[1]+1+n])
        if m == 0:
            return 0
    return m

print(check(rebrand(PLOCHA), [3,2], [3,3]))


