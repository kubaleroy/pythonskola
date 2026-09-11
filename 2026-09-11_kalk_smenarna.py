import requests
from_c = input("Z meny: ")
to_c = input("Do meny: ")
base = float(input(f"Prevest kolik z {from_c} do {to_c}: "))
link = f"https://api.frankfurter.dev/v2/rates?base={from_c.upper()}&quotes={to_c.upper()}"
x = requests.get(link)
rate = float(str(x.content).split(",")[-1].split(":")[-1].split("}")[0])
print(f"{base} {from_c} = {rate*base:.2f} {to_c}")