"""
Analýza

Vstupy: int sekund kladny cele cislo vetsi nez 0

Výstupy: vypište, kolik je to hodin, minut a sekund, ve tvaru „H h M min S s“

Omezení/okrajové případy: 0, desetina mista, ..

Návrh

Kroky: input-> prepsat typ -> vzit pocet hodin a zbytek -> ze zbytku vzit pocet minut a 
"""
input = input("Cas v sekundach: ")
if "." in input:
    print("Zadfej cele cislo")
    exit()
if "-" in input:
    print("Zadej kladne cislo")
    exit()
input = int(input)
h = input//3600
zbytekh = input%3600
m = zbytekh//60
s = input%60
print(f"{(str(h)+" h") if h != 0 else ""} {(str(m)+" min") if m != 0 else ""} {(str(s)+" s")}")