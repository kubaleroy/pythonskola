

#nejdelsi retezec stejnych znaku primo po sobe 
def nejdelsi_retezec():
    x = input("str>>")
    longest = 0
    run = 0
    last = ""
    for i in x:
        if i == last:
            run += 1
        else:
            if run > longest:
                longest = run
            run = 1
            last = i
    print(longest)
#nejdelsi_retezec()
