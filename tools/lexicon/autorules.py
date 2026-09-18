"""Règles automatiques : les classes de mots que l'auteur supprime systématiquement.

Une règle **n'écrit rien** dans `decisions.csv` : elle est activée dans
`data/lexicon/auto_rules.json` (versionné) puis appliquée à l'export du lexique et à la file de
tri. Trois conséquences voulues :

- le fichier des décisions ne garde que les choix faits à la main (ADR 0001) ;
- une règle se désactive d'un mot, sans réécrire l'historique ;
- une décision explicite « garder » l'emporte toujours sur une règle.

Chaque règle est une condition SQL sur `FROM_CLAUSE` (la table des mots, jointe à son lemme),
ce qui permet de l'appliquer à l'export comme à la file de tri sans dupliquer la logique.
"""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Les règles parlent du mot (`w`) et de son lemme (`l`)
FROM_CLAUSE = "words w LEFT JOIN words l ON l.norm = w.lemma_norm"
# La graphie affichée — celle qui part dans le lexique exporté. C'est sur elle que porte la mesure
# (119 mots triés à la main, 119 supprimés), donc c'est elle que la règle de suppression regarde.
COMPOSED_FORM = ("(json_extract(w.display_forms, '$[0]') LIKE '% %' "
                 "OR json_extract(w.display_forms, '$[0]') LIKE '%''%' "
                 "OR json_extract(w.display_forms, '$[0]') LIKE '%’%')")

# N'importe laquelle des graphies. Beaucoup de mots courants ont une graphie secondaire en deux mots
# (« avoir » / « à voir », « savoir » / « s'avoir ») : ce test ne sert donc **jamais** à supprimer,
# seulement à écarter un mot du regroupement par famille, où il n'a rien à faire.
ANY_COMPOSED_FORM = ("EXISTS (SELECT 1 FROM json_each(w.display_forms) "
                     "WHERE json_each.value LIKE '% %' OR json_each.value LIKE '%''%' "
                     "OR json_each.value LIKE '%’%')")


@dataclass(frozen=True)
class Rule:
    id: str
    label: str
    evidence: str
    sql: str
    default: bool = False


RULES = (
    Rule(
        id="formes-composees",
        label="Formes en plusieurs mots ou avec apostrophe (« a priori », « aux WC »)",
        evidence="119 mots de cette classe triés à la main : 119 supprimés, aucun gardé.",
        sql=COMPOSED_FORM,
        default=True,
    ),
    Rule(
        id="inconnues-sans-definition",
        label="6 lettres et plus, absentes de Lexique, sans définition ni lemme",
        evidence="94,6 % des mots de cette classe triés à la main ont été supprimés "
                 "(100 % à partir de 6 lettres).",
        sql="w.length >= 6 AND w.zipf = 0 AND w.lemma_norm IS NULL AND w.definition IS NULL",
        default=True,
    ),
    Rule(
        id="flexions-rares-longues",
        label="9 lettres et plus, formes fléchies de verbes rares ou inconnus",
        evidence="Aucune forme de 7 lettres ou plus n'a été gardée (22 jugements), mais la classe "
                 "est très large : à n'activer qu'après avoir regardé l'aperçu.",
        sql="w.length >= 9 AND COALESCE(w.definition_kind, '') != 'own' AND COALESCE(l.zipf, 0) < 2",
        default=False,
    ),
)

RULES_BY_ID = {rule.id: rule for rule in RULES}
DEFAULT_RULES = tuple(rule.id for rule in RULES if rule.default)


class UnknownRuleError(ValueError):
    """Règle inconnue : le fichier de règles ou la ligne de commande nomme une règle qui n'existe pas."""


def _validated(ids) -> tuple[str, ...]:
    unknown = [rule_id for rule_id in ids if rule_id not in RULES_BY_ID]
    if unknown:
        known = ", ".join(RULES_BY_ID)
        raise UnknownRuleError(f"règle inconnue : {', '.join(unknown)} (règles connues : {known})")
    # Ordre stable, sans doublon
    return tuple(rule.id for rule in RULES if rule.id in set(ids))


def load_enabled(path) -> tuple[str, ...]:
    """Règles activées (fichier absent : aucune règle, le lexique reste tel quel)."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return ()
    content = json.loads(path.read_text(encoding="utf-8"))
    return _validated(content.get("regles", []))


def save_enabled(path, ids) -> tuple[str, ...]:
    enabled = _validated(ids)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "regles": list(enabled),
        "commentaire": "Règles automatiques appliquées à l'export et au tri "
                       "(python -m tools.lexicon autorules).",
    }
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return enabled


def condition(ids) -> str:
    """Condition SQL vraie pour les mots visés par au moins une règle activée (vide si aucune).

    Les mots très courants (`suggestion = 'keep'`, zipf ≥ 3,5) sont hors d'atteinte des règles :
    ils ne passent déjà pas par le tri, et une règle ne doit jamais les retirer du lexique.
    Sans cette garde, « est », « avec » ou « avoir » disparaîtraient des grilles.
    """
    enabled = _validated(ids)
    if not enabled:
        return ""
    rules = " OR ".join(RULES_BY_ID[rule_id].sql for rule_id in enabled)
    return f"(w.suggestion != 'keep' AND ({rules}))"


def matches(db_path, ids) -> set[str]:
    """Mots visés par les règles activées (ensemble vide si aucune règle)."""
    clause = condition(ids)
    if not clause:
        return set()
    connection = sqlite3.connect(db_path)
    try:
        return {row[0] for row in connection.execute(f"SELECT w.norm FROM {FROM_CLAUSE} WHERE {clause}")}
    finally:
        connection.close()


def preview(db_path, decisions_path, ids=None, sample: int = 10) -> dict:
    """Aperçu règle par règle : combien de mots, lesquels, et ce qui est déjà décidé à la main.

    Sert au `--dry-run` : rien n'est écrit, tout est là pour décider d'activer ou non.
    """
    from .decisions import KEEP, effective_decisions, read_decisions

    decisions = effective_decisions(read_decisions(decisions_path))
    kept = {word for word, decision in decisions.items() if decision == KEEP}
    connection = sqlite3.connect(db_path)
    try:
        report = {}
        for rule in RULES:
            if ids is not None and rule.id not in ids:
                continue
            # Même garde que `condition` : l'aperçu ne doit pas annoncer des mots que la règle
            # ne touchera jamais (les très courants sont hors d'atteinte).
            rows = connection.execute(
                f"SELECT w.norm, w.length, json_extract(w.display_forms, '$[0]') FROM {FROM_CLAUSE} "
                f"WHERE w.suggestion != 'keep' AND ({rule.sql}) ORDER BY w.queue_order"
            ).fetchall()
            concerned = [row for row in rows if row[0] not in kept]
            report[rule.id] = {
                "label": rule.label,
                "evidence": rule.evidence,
                "default": rule.default,
                "words": len(concerned),
                "words_up_to_11": sum(1 for row in concerned if row[1] <= 11),
                "kept_by_author": len(rows) - len(concerned),
                "already_decided": sum(1 for row in concerned if row[0] in decisions),
                "sample": [row[2] or row[0] for row in concerned[:sample]],
            }
        return report
    finally:
        connection.close()
