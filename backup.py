import os
import time
import datetime
date = datetime.date.fromtimestamp(time.time())
add = r"git add ."
no = 0

with open("commits.txt") as txt2:
    txt = txt2.readlines()
txtold = "\n".join(txt)
def get_commit_num(txt):
    written = False
    for line in txt:
        for item in line.split(" "):
            if str(item) == str(date):
                written = True
                continue
            if written:
                no = int(item)
                txt2.close()
                return no
    return 0
writetxt = open("commits.txt", "w")
numcoms = get_commit_num(txt)
dayver = ""
if numcoms == 0:
    txtold += f"\n{date} 1"
else:
    help1 = txtold.split("\n")
    help1[-1] = f"{date} {numcoms + 1}"
    while "" in help1:
        help1.remove("")
    txtold = "\n".join(help1)
    dayver = f"/{numcoms}"
writetxt.write(txtold)
writetxt.close()

commit = f"git commit -m \"{date}{numcoms}\""
push = f"git push -u origin main"
os.system(add)
os.system(commit)
os.system(push)