"""Fréquence (échelle zipf) et suggestion d'aide à la décision."""

import math
from dataclasses import asdict, dataclass

KEEP = "keep"                    # très courant : gardé sans passer par le tri
LIKELY_KEEP = "likely_keep"
REVIEW = "review"
# Absent de Lexique et sans définition propre (au mieux « forme fléchie de X ») : très probablement rare
LIKELY_DELETE = "likely_delete"
SUGGESTIONS = (KEEP, LIKELY_KEEP, REVIEW, LIKELY_DELETE)


@dataclass(frozen=True)
class Thresholds:
    # zipf = log10(occurrences par milliard) : 3 = 1 par million, 6 = 1 pour 1 000
    auto_keep_zipf: float = 3.5
    likely_keep_zipf: float = 2.5

    def as_dict(self) -> dict:
        return asdict(self)


def zipf_from_per_million(per_million: float) -> float:
    return round(math.log10(per_million) + 3, 2) if per_million > 0 else 0.0


def suggest(zipf: float, has_own_definition: bool, thresholds: Thresholds = Thresholds()) -> str:
    """Le Wiktionnaire définit presque toutes les conjugaisons : seule une définition propre au mot
    (pas « forme fléchie de X ») sauve un mot absent de Lexique."""
    if zipf >= thresholds.auto_keep_zipf:
        return KEEP
    if zipf >= thresholds.likely_keep_zipf:
        return LIKELY_KEEP
    if zipf == 0 and not has_own_definition:
        return LIKELY_DELETE
    return REVIEW
