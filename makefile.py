import time, datetime, os
date = datetime.date.fromtimestamp(time.time())
name = input("Jmeno souboru:\n>>")
if name.startswith("XxX"):
    date = "23LSalatJ"
    name = name.replace("XxX", "", 1)
with open(f"{os.path.dirname(os.path.realpath(__file__))}\\{date}_{name}.py", "w") as f:
    f.close()
    