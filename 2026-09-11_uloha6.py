n = input("Kolik cisel: ")
l = [float(input(f"Cislo {x+1}: ")) for x in range(int(n))]
print(f"součet= {sum(l):.2f}, průměr= {sum(l)/int(n):.2f}, maximum= {max(l):.2f} a minimum= {min(l):.2f}")