import os
import time
import datetime
date = datetime.date.fromtimestamp(time.time())
add = r"git add ."
written = False
no = 0
txt = open("commits.txt", "r")
txtold = txt.read()

def get_commit_num():
    for line in txt.read():
        for item in line.split(" "):
            if item == date:
                written = True
                continue
            if written:
                no = int(item)
                txt.close()
                return no
    return 0

txt = open("commits.txt", "w")
numcoms = get_commit_num()
if numcoms == 0:
    txtold += f"\n{date} 1"
else:
    txtold[:-1] = f"\n{date} {numcoms +1}"


commit = f"git commit -m \"{date}\""
