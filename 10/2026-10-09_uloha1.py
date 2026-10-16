n = int(input("Kolik známek zadáš? "))
znamky = []
for _ in range(n):
    z = int(input("Zadej známku (1-5): "))
    znamky.append(z)

# TODO: spočítej průměr, nejlepší (= nejnižší číslo) a nejhorší (= nejvyšší číslo) známku
# a vypiš je, podobně jako ve společné ukázce výše.
print(f"prumer: {sum(znamky)/len(znamky)} nej: {min(znamky)} nejhorsi: {max(znamky)}")