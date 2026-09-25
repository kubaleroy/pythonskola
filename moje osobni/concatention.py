s = "barfoofoobarthefoobarman"
words = ["foo","bar","the"]
for i in range(len(s)-len(words)*len(words[0])):
    if s[i:i+len(words[0])] in words:
    

