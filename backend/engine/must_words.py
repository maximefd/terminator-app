"""
Mots obligatoires : vérification préalable ([ADR 0007](../../docs/adr/0007-contrat-de-generation.md)).

La vraie limite n'est pas un nombre fixe, c'est le layout : dix mots obligatoires sont impossibles
sur un 6x7 et raisonnables sur un grand format. Ces règles répondent donc **avant toute résolution**,
en comparant les mots demandés aux emplacements réellement disponibles. Pures : ni Flask ni fichier.
"""


def slot_lengths(slots) -> dict[int, int]:
    """Nombre d'emplacements par longueur : {5: 3, 6: 2…}."""
    lengths: dict[int, int] = {}
    for slot in slots:
        lengths[slot["length"]] = lengths.get(slot["length"], 0) + 1
    return lengths


def check_must_words(slots, words) -> list[dict]:
    """Impossibilités certaines, expliquées mot par mot : `[{word, problem}]` (vide si tout peut entrer).

    Deux règles suffisent à garantir qu'un refus est certain : un mot plus long que le plus long
    emplacement n'entrera jamais, et n mots d'une longueur donnée ont besoin de n emplacements de
    cette longueur. Le reste (les croisements) ne peut se savoir qu'en résolvant.
    """
    available = slot_lengths(slots)
    longest = max(available, default=0)
    problems = []

    wanted: dict[int, list[str]] = {}
    for word in words:
        length = len(word)
        if length > longest:
            problems.append({
                "word": word,
                "problem": f"{length} lettres : le plus long emplacement de ce layout en compte {longest}.",
            })
            continue
        wanted.setdefault(length, []).append(word)

    for length, asked in sorted(wanted.items()):
        slots_here = available.get(length, 0)
        if len(asked) > slots_here:
            for word in asked:
                problems.append({
                    "word": word,
                    "problem": f"{len(asked)} mots de {length} lettres demandés pour "
                               f"{slots_here} emplacement(s) de cette longueur.",
                })
    return problems
