import time, datetime
date = datetime.date.fromtimestamp(time.time())
name = input("Jmeno souboru:\n>>")
with open(f"{date}_{name}.py", "w") as f:
    f.close()
    