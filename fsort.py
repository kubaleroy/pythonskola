import os
#format YYYY-MM-DD
# f MM
path =r"C:\Users\23lsalatj\Desktop\python"
files = []
months = []
for file in os.listdir(path):
    if file.startswith("202") and len(file.split("-"))>=3 and file.endswith((".py")):
        files.append(file)
        m = file.split("-")[1]
        if m not in months:
            months.append(m)
#print(os.listdir(path=path))
print(files)
for m in months:
    if not os.path.isdir(path+rf"\{m}"):
        os.makedirs(path+rf"\{m}")
for f in files:
    m = f.split("-")[1]
    fp = path+fr"\{m}\{f}"
    fpo = path+fr"\{f}"
    ff = path+fr"\{m}"
    if not os.path.exists(fp):
        os.system(fr'move "{fpo}" "{ff}"')
        #print(ff,"\n",fp)