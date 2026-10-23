s = "barfoofoobarthefoobarman"
words = ["foo","bar","the"]
for i in range(len(s)-len(words)*len(words[0])):
    w = words.copy()
    r = i
    conti = lambda st: s[st:st+len(words[0])] in w
    while conti(r):
        w.remove(s)
    
        
    

