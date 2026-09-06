
predmety = {
    "ux": [
        "Jan Burian", "Jindřich Cvrček", "Daniel Dražan", 
        "Jan Korecký", "Duc Khánh Le", "Štěpán Pajskr", 
        "Tomáš Pfortner", "Zbyněk Sluka", "Šimon Soldán", 
        "Martin Šebek", "Martin Šerák", "Dominik Škréta", 
        "Jáchym Vršek"
        ],
    "p" : [
        "Vojtěch Čapek", "Maxime Frank", "Vojtěch Fréhar", 
        "Martin Chvojka", "Boris Kvasnička", "David Martinec", 
        "Jáchym Michálko-Kačkoš", "Matěj Moucha", "Jan Paulů", 
        "Antonín Semerák", "Ela Scholzová", "Martin Slavík", 
        "Jakub Šalát", "Michael Táborský", "Martina Urbanová", 
        "Matěj Zabloudil"
        ],
    "am": [
        "Jindřich Cvrček", "Vojtěch Čapek", "Daniel Dražan",
        "Martin Chvojka", "Jan Korecký", "Boris Kvasnička",
        "Duc Khánh Le", "David Martinec", "Matěj Moucha", 
        "Jan Paulů", "Ela Scholzová", "Martin Slavík", 
        "Jakub Šalát", "Dominik Škréta", "Michael Táborský"],
    "ls": [
        "Jan Burian", "Jáchym Michálko-Kačkoš", "Martin Šebek", 
        "Martina Urbanová", "Jáchym Vršek"
        ],
    "sg": [
        "Maxime Frank", "Vojtěch Fréhar", "Štěpán Pajskr",
        "Tomáš Pfortner", "Antonín Semerák", "Zbyněk Sluka", 
        "Šimon Soldán", "Martin Šerák", "Matěj Zabloudil"
        ],
    "a1" : [
        "Jan Burian", "Jindřich Cvrček", "Martin Chvojka", 
        "Jan Korecký", "Duc Khánh Le", "David Martinec",
        "Jáchym Michálko-Kačkoš", "Jakub Šalát", "Martin Šebek", 
        "Martin Šerák", "Dominik Škréta", "Martina Urbanová", 
        "Matěj Zabloudil"
        ],
    "a2" : [
        "Vojtěch Čapek", "Boris Kvasnička", "Maxime Frank",  
        "Daniel Dražan", "Štěpán Pajskr", "Tomáš Pfortner", 
        "Michael Táborský", "Vojtěch Fréhar", "Matěj Moucha", 
        "Jan Paulů", "Antonín Semerák", "Jáchym Vršek", 
        "Ela Scholzová", "Šimon Soldán", "Martin Slavík",
        "Zbyněk Sluka"
        ],
    "n2" : [ 
        "Maxime Frank", "Jan Korecký", "Boris Kvasnička", 
        "Jáchym Michálko-Kačkoš", "David Martinec", "Matěj Moucha", 
        "Jan Paulů", "Martin Slavík", "Ela Scholzová", 
        "Jakub Šalát", "Martina Urbanová", "Matěj Zabloudil", 
        "Martin Šebek", "Tomáš Pfortner", "Šimon Soldán"
        ],
    "n1" : [
        "Jan Burian", "Jindřich Cvrček", "Daniel Dražan", 
        "Zbyněk Sluka", "Martin Šerák", "Dominik Škréta", 
        "Jáchym Vršek", "Michael Táborský", "Antonín Semerák",
        "Martin Chvojka", "Vojtěch Čapek", "Vojtěch Fréhar",
        "Duc Khánh Le", "Štěpán Pajskr"
        ],
    "me" : [
        "Jakub Šalát", "Martina Urbanová", "Daniel Dražan", 
        "Ela Scholzová", "Dominik Škréta", "Duc Khánh Le", 
        "Jindřich Cvrček", "Martin Chvojka", "Jan Korecký", 
        "Matěj Zabloudil", "Michael Táborský", "David Martinec", 
        "Tomáš Pfortner", "Šimon Soldán"
        ],
    "el" : [
        "Jan Burian", "Vojtěch Čapek", "Maxime Frank", 
        "Jáchym Michálko-Kačkoš", "Jan Paulů", "Antonín Semerák", 
        "Zbyněk Sluka", "Štěpán Pajskr", "Martin Šebek", 
        "Martin Šerák", "Matěj Moucha", "Jáchym Vršek",
        "Martin Slavík", "Boris Kvasnička", "Vojtěch Fréhar"
        ]
}

# How much a shared subject costs a pair.
scoring = {
    "p": 0.6,
    "ux": 0.6,
    "am": 0.1,
    "ls": 0.5,
    "sg": 0.5,
    "a1": 2,
    "a2": 2,
    "n2": 2,
    "n1": 2,
    "me": 0.5,
    "el": 0.5
}

# How deep to look for an alternative when the best option is already taken.
RANK_DEPTH = 4


def sort_by_surname(names):
    return sorted(names, key=lambda name: (name.split(" ")[-1], name))


def get_score(predmety, scoring, dvojice):
    """Weight of the subjects both members of the pair attend."""
    return sum(
        scoring[predmet]
        for predmet, lide in predmety.items()
        if dvojice[0] in lide and dvojice[1] in lide
    )


def get_same_predmet(predmety, dvojice):
    """Subjects both members of the pair attend."""
    return [
        predmet
        for predmet, lide in predmety.items()
        if dvojice[0] in lide and dvojice[1] in lide
    ]


def get_permutations(predmety):
    """Every possible pairing of an a1 student with an a2 student."""
    return [[i, j] for i in predmety["a1"] for j in predmety["a2"]]


def remove_candidates_from_rank(rankx, candidate):
    """Drop a candidate that got paired off from every option list."""
    for options in rankx:
        if candidate in options:
            options.remove(candidate)
    return rankx


def remove_duplicates(sequence):
    unique = []
    for item in sequence:
        if item not in unique:
            unique.append(item)
    return unique


def get_missing(predmety, current_candidates):
    """Students that none of the pairs covers."""
    missing = predmety["a1"] + predmety["a2"]
    for dvojice in current_candidates:
        for person in dvojice:
            if person in missing:
                missing.remove(person)
            else:
                print(f"Error removing {person}: not in the list")
    return missing


def get_best_for_people(predmety, scoring, _ranks=None):
    if _ranks is None:
        _ranks = [-1 for _ in predmety["a1"]]
    best = []
    permutations = get_permutations(predmety)
    for person in predmety["a1"]:
        limit = _ranks[predmety["a1"].index(person)]
        best_for_person = [float("inf"), []]
        for dvojice in permutations:
            if person not in dvojice:
                continue
            score = get_score(predmety, scoring, dvojice)
            if limit < score < best_for_person[0]:
                best_for_person = [score, dvojice]
            elif score == best_for_person[0]:
                best_for_person[1].append(dvojice[1])
        best.append(remove_duplicates(best_for_person[1]))
    return best


def get_realistic_best(predmety, scoring, rank):
    best = get_best_for_people(predmety, scoring)
    for _ in range(1, rank):
        scores = [get_score(predmety, scoring, options) for options in best]
        best = get_best_for_people(predmety, scoring, scores)
    return best


def pick_pairs(ranks):
    final = []
    for i in range(len(ranks[0])):
        for rank in ranks:
            if len(rank[i]) <= 1:
                continue
            final.append(rank[i][:2])
            partner = rank[i][1]
            for other in ranks:
                if len(other[i]) > 1:
                    remove_candidates_from_rank(other, partner)
            break
    return final


def get_best_for_extra(predmety, scoring, extra):
    best = [float("inf"), [extra]]
    for person in predmety["a1"]:
        score = get_score(predmety, scoring, [person, extra])
        if score < best[0]:
            best = [score, [extra, person]]
        elif score == best[0]:
            best[1].append(person)
    return best[1]


def main():
    for predmet, lide in predmety.items():
        predmety[predmet] = sort_by_surname(lide)

    ranks = [get_realistic_best(predmety, scoring, rank)
             for rank in range(1, RANK_DEPTH + 1)]
    final = pick_pairs(ranks)

    for dvojice in final:
        print(dvojice,
              get_same_predmet(predmety, dvojice),
              get_score(predmety, scoring, dvojice))

    extras = get_missing(predmety, final)
    print("navic", extras)

    for extra in extras:
        options = get_best_for_extra(predmety, scoring, extra)
        print(options,
              get_same_predmet(predmety, [options[1], extra]),
              get_score(predmety, scoring, [options[1], extra]))


if __name__ == "__main__":
    main()
