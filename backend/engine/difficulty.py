"""
Difficulté d'une demande de mots imposés, estimée **sans générer** (#73).

L'auteur tape ses mots avant de lancer la génération : autant lui dire tout de suite ce qu'ils
coûtent. Les taux ci-dessous ne sont pas décrétés, ils viennent de **4 700 générations mesurées**
(voir `backend/benchmarks/README.md`) : trois facteurs ressortent, dans cet ordre.

1. **La longueur du mot le plus long** — facteur dominant. Trois mots de 6 lettres au plus
   réussissent 67 % du temps, contre 39 % sans plafond.
2. **La présence d'une lettre rare** (`Z`, `W`, `K`, `X`, `Q`, `Y`, `J`) : les mots refusés en
   contiennent deux fois plus souvent. Un `Z` doit tomber en cul-de-sac ou finir un verbe en `-EZ`.
3. **Le nombre de mots** : 1 mot 94 %, 2 mots 82 %, 3 mots 46 %.

Pur : ni Flask, ni base, ni lecture de fichier.
"""

# Lettres qui se croisent mal : peu de mots du lexique en contiennent
RARE_LETTERS = frozenset("ZWKXQYJ")

BANDS = (("2-5", 5), ("6-7", 7), ("8-9", 9), ("10+", 99))

# (nombre de mots, bande de longueur du plus long, contient une lettre rare) -> taux de réussite
# mesuré. Seules les cases d'au moins 25 générations figurent ici.
MEASURED_SUCCESS = {
    (1, "2-5", False): 1.00, (1, "2-5", True): 0.93,
    (1, "6-7", False): 0.97, (1, "6-7", True): 0.90,
    (1, "8-9", False): 0.90, (1, "8-9", True): 0.67,
    (1, "10+", False): 0.84, (1, "10+", True): 0.60,
    (2, "2-5", False): 0.87, (2, "2-5", True): 0.92,
    (2, "6-7", False): 0.87, (2, "6-7", True): 0.73,
    (2, "8-9", False): 0.58,
    (2, "10+", False): 0.27,
    (3, "2-5", False): 0.82, (3, "2-5", True): 0.72,
    (3, "6-7", False): 0.61, (3, "6-7", True): 0.36,
    (3, "8-9", False): 0.52, (3, "8-9", True): 0.26,
    (3, "10+", False): 0.26, (3, "10+", True): 0.13,
}

# Pénalité appliquée aux cases « lettre rare » non mesurées (moins de 25 générations) : rapport
# médian observé entre les cases rares et non rares mesurées.
RARE_PENALTY = 0.85

# Classes de taille, en nombre d'emplacements du format. La taille compte, mais **son effet
# s'inverse selon la demande** (mesuré) : pour des mots courts la petite grille gagne, pour des
# mots longs la grande. Un mot long exige un emplacement long, que seuls les grands formats
# offrent en nombre ; un mot court sur une grande grille signifie surtout beaucoup d'autres mots
# à placer à côté.
SIZE_CLASSES = (("petite", 21), ("moyenne", 43), ("grande", 10_000))

# Taux mesurés par (nombre de mots, bande, lettre rare, classe de taille). Bandes regroupées en
# trois ici : par taille, les cases de « 8-9 » et « 10+ » n'atteignaient pas 30 générations.
MEASURED_BY_SIZE = {
    (1, "2-5", False): {"petite": 1.00, "moyenne": 1.00, "grande": 1.00},
    (1, "6-7", False): {"petite": 0.92, "moyenne": 1.00, "grande": 1.00},
    (1, "8+", False): {"petite": 0.83, "moyenne": 0.81, "grande": 0.83},
    (2, "2-5", False): {"petite": 1.00, "moyenne": 0.94, "grande": 0.77},
    (2, "2-5", True): {"petite": 0.98, "moyenne": 0.97, "grande": 0.74},
    (2, "6-7", False): {"petite": 0.95, "moyenne": 0.89, "grande": 0.74},
    (2, "6-7", True): {"petite": 0.78, "grande": 0.61},
    (3, "2-5", False): {"petite": 0.93, "moyenne": 0.74, "grande": 0.84},
    (3, "2-5", True): {"petite": 0.67},
    (3, "6-7", False): {"petite": 0.66, "moyenne": 0.74, "grande": 0.61},
    (3, "6-7", True): {"petite": 0.35, "moyenne": 0.40, "grande": 0.38},
    (3, "8+", False): {"petite": 0.33, "moyenne": 0.20, "grande": 0.45},
    (3, "8+", True): {"petite": 0.13, "moyenne": 0.07, "grande": 0.31},
}

# Seuils des niveaux, en taux de réussite estimé
LEVELS = ((0.90, "facile"), (0.70, "moyen"), (0.40, "difficile"), (0.0, "très difficile"))


def length_band(length: int) -> str:
    """Bande de longueur d'un mot, telle que les mesures la découpent."""
    return next(name for name, limit in BANDS if length <= limit)


def rare_letters(word: str) -> list[str]:
    """Lettres rares du mot, dans l'ordre d'apparition et sans doublon."""
    seen: list[str] = []
    for letter in word:
        if letter in RARE_LETTERS and letter not in seen:
            seen.append(letter)
    return seen


def level_of(success_rate: float) -> str:
    return next(name for threshold, name in LEVELS if success_rate >= threshold)


def success_rate(count: int, band: str, rare: bool) -> tuple[float, bool]:
    """Taux estimé et « est-il directement mesuré ? ».

    Au-delà de trois mots, rien n'a été mesuré : on applique le taux à trois mots, qui est alors
    une **borne haute** — ajouter un mot n'a jamais fait monter le taux.
    """
    key = (min(count, 3), band, rare)
    if key in MEASURED_SUCCESS:
        return MEASURED_SUCCESS[key], count <= 3
    base = MEASURED_SUCCESS.get((min(count, 3), band, False))
    if base is None:  # bande sans aucune mesure : on reste prudent
        return 0.0, False
    return (round(base * RARE_PENALTY, 2), False) if rare else (base, False)


def size_class(slots: int | None) -> str | None:
    """Classe de taille d'un format, d'après son nombre d'emplacements (None si inconnu)."""
    if not slots:
        return None
    return next(name for name, limit in SIZE_CLASSES if slots <= limit)


def _wide_band(band: str) -> str:
    """Bandes regroupées pour la table par taille, où « 8-9 » et « 10+ » manquaient d'échantillon."""
    return "8+" if band in ("8-9", "10+") else band


def success_rate_for_size(count: int, band: str, rare: bool, klass: str | None) -> tuple[float, bool] | None:
    """Taux mesuré pour cette taille, ou None si la case n'a pas d'échantillon suffisant."""
    if klass is None:
        return None
    cell = MEASURED_BY_SIZE.get((min(count, 3), _wide_band(band), rare))
    if cell is None or klass not in cell:
        return None
    return cell[klass], count <= 3


def word_difficulty(word: str) -> dict:
    """Ce que coûte ce mot, **seul**, tel qu'on peut le dire dès qu'il est tapé."""
    band = length_band(len(word))
    rares = rare_letters(word)
    rate, measured = success_rate(1, band, bool(rares))
    reasons = []
    if band in ("8-9", "10+"):
        reasons.append(f"{len(word)} lettres : peu d'emplacements l'accueillent, et tous ses croisements "
                       f"doivent tomber juste")
    if rares:
        reasons.append(f"contient {', '.join(rares)} : ces lettres se croisent mal")
    return {"word": word, "length": len(word), "band": band, "rare_letters": rares,
            "success_rate": rate, "level": level_of(rate), "measured": measured, "reasons": reasons}


def request_difficulty(words, slots: int | None = None) -> dict:
    """Difficulté de la demande entière, à afficher au fur et à mesure que l'auteur ajoute des mots.

    `slots` : nombre d'emplacements du format visé, quand l'auteur en a choisi un. Le taux en
    dépend — et pas dans le sens qu'on croirait : pour des mots courts la petite grille gagne,
    pour des mots longs la grande. Sans taille choisie, l'estimation agrège tous les formats.
    """
    words = list(words)
    if not words:
        return {"words": [], "success_rate": 1.0, "level": "facile", "measured": True,
                "hardest": None, "advice": None, "size_class": size_class(slots)}

    details = [word_difficulty(word) for word in words]
    band = length_band(max(len(word) for word in words))
    rare = any(detail["rare_letters"] for detail in details)
    klass = size_class(slots)
    par_taille = success_rate_for_size(len(words), band, rare, klass)
    rate, measured = par_taille if par_taille else success_rate(len(words), band, rare)
    hardest = min(details, key=lambda detail: (detail["success_rate"], -detail["length"]))

    advice = None
    if rate < 0.70:
        advice = (f"« {hardest['word']} » est ce qui pèse le plus. En mot souhaité plutôt "
                  f"qu'obligatoire, il sera placé s'il rentre, sans faire échouer la grille.")
    return {"words": details, "success_rate": rate, "level": level_of(rate), "measured": measured,
            "hardest": hardest["word"], "advice": advice, "size_class": klass}
