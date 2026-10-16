import time, datetime
date = datetime.date.fromtimestamp(time.time())
name = input("Jmeno souboru:\n>>")
if name.startswith("XxX"):
    date = "23LSalatJ"
with open(f"{date}_{name[3:]}.py", "w") as f:
    f.close()
    