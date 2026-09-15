import gzip
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
# Pour vérifier l'équivalence de normalisation avec le backend
sys.path.insert(0, str(REPO_ROOT / "backend"))

DELA_LINES = [
    "PORTE;porté;Forme fléchie de 'porté'",
    "PORTE;porte;Forme fléchie de 'porte'",
    "PORTES;portes;Forme fléchie de 'portes'",
    "ETE;été;Forme fléchie de 'été'",
    "ETE;étê;Forme fléchie de 'étê'",
    "OUVRAGE;ouvrage;Forme fléchie de 'ouvrage'",
    "OUVRAGEAMES;ouvrageâmes;Forme fléchie de 'ouvrageâmes'",
    "OUVRAGER;ouvrager;Forme fléchie de 'ouvrager'",
    "AABAM;aabam;Forme fléchie de 'aabam'",
    "A PRIORI;a priori;Forme fléchie de 'a priori'",
    "X;x;Forme fléchie de 'x'",
]

LEXIQUE_ROWS = [
    # ortho, phon, lemme, cgram, freqfilms2, freqlivres, islem
    ("porte", "pORt", "porte", "NOM", "288.39", "536.96", "1"),
    ("porte", "pORt", "porter", "VER", "93.05", "79.05", "0"),
    ("portes", "pORt", "porte", "NOM", "50", "60", "0"),
    ("été", "ete", "été", "NOM", "100", "150", "1"),
    ("été", "ete", "être", "AUX", "500", "300", "0"),
    ("ouvrage", "uvRaZ", "ouvrage", "NOM", "0.3", "0.1", "1"),
    ("a priori", "apRijORi", "a priori", "ADV", "0.5", "0.3", "1"),
]

WIKTIONARY_RECORDS = [
    # Nom propre placé en premier : doit être ignoré (définition et forme affichée)
    {"word": "Porte", "lang_code": "fr", "pos": "name", "senses": [{"glosses": ["Nom de famille."]}]},
    # Préfixe et sigle : ignorés eux aussi
    {"word": "porte-", "lang_code": "fr", "pos": "prefix", "senses": [{"glosses": ["Préfixe désignant ce qui porte."]}]},
    {"word": "ETE", "lang_code": "fr", "pos": "noun", "senses": [{"glosses": ["Sigle d'un organisme."]}]},
    {"word": "été", "lang_code": "fr", "pos": "noun", "senses": [{"glosses": ["La plus chaude des saisons."]}]},
    {"word": "ouvrage", "lang_code": "fr", "pos": "noun",
     "senses": [{"glosses": ["Œuvre produite par un travail."]}]},
    {"word": "ouvrageâmes", "lang_code": "fr", "pos": "verb",
     "senses": [{"glosses": ["Première personne du pluriel du passé simple de ouvrager."],
                 "tags": ["form-of"], "form_of": [{"word": "ouvrager"}]}]},
    {"word": "ouvrager", "lang_code": "fr", "pos": "verb",
     "senses": [{"glosses": ["Travailler avec soin."]}]},
    {"word": "porte", "lang_code": "fr", "pos": "verb",
     "senses": [{"glosses": ["Première personne du singulier de l’indicatif présent de porter."],
                 "tags": ["form-of"], "form_of": [{"word": "porter"}]}]},
    {"word": "porte", "lang_code": "fr", "pos": "noun",
     "senses": [{"glosses": ["Ouverture permettant le passage."]}]},
    {"word": "door", "lang_code": "en", "pos": "noun", "senses": [{"glosses": ["A door."]}]},
    {"word": "vide", "lang_code": "fr", "pos": "noun", "senses": []},
]


@pytest.fixture
def dela_file(tmp_path):
    path = tmp_path / "dela.csv"
    path.write_text("\n".join(DELA_LINES) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def lexique_file(tmp_path):
    path = tmp_path / "Lexique383.tsv"
    lines = ["ortho\tphon\tlemme\tcgram\tfreqfilms2\tfreqlivres\tislem"]
    lines += ["\t".join(row) for row in LEXIQUE_ROWS]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def wiktionary_file(tmp_path):
    path = tmp_path / "wiktionary.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for record in WIKTIONARY_RECORDS:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path
