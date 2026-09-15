import json
import sqlite3

from tools.lexicon.build import build_lexicon


def fetch_words(db_path):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        return {row["norm"]: dict(row) for row in connection.execute("SELECT * FROM words")}
    finally:
        connection.close()


def test_build_combines_the_three_sources(dela_file, lexique_file, wiktionary_file, tmp_path):
    db_path = tmp_path / "build" / "lexicon.sqlite"

    stats = build_lexicon(dela_file, lexique_file, db_path, wiktionary_file, log=lambda _: None)

    words = fetch_words(db_path)
    assert stats.words == len(words) == 8
    assert words["PORTE"]["suggestion"] == "keep"
    assert (words["PORTE"]["definition"], words["PORTE"]["definition_kind"]) == ("Ouverture permettant le passage.", "own")
    # « porté » vient en premier dans le DELA, mais « porte » est l'orthographe la plus fréquente
    assert json.loads(words["PORTE"]["display_forms"]) == ["porte", "porté"]
    assert words["ETE"]["lemma"] == "être"
    assert json.loads(words["ETE"]["display_forms"]) == ["été", "étê"]
    assert (words["OUVRAGE"]["zipf"], words["OUVRAGE"]["suggestion"]) == (2.3, "review")
    assert words["APRIORI"]["suggestion"] == "likely_keep"
    # Absent de Lexique, défini seulement comme forme fléchie : très probablement rare
    assert (words["OUVRAGEAMES"]["definition_kind"], words["OUVRAGEAMES"]["suggestion"]) == ("inflection", "likely_delete")
    # Absent de Lexique mais avec une définition propre : à trier
    assert (words["OUVRAGER"]["definition_kind"], words["OUVRAGER"]["suggestion"]) == ("own", "review")
    assert (words["AABAM"]["zipf"], words["AABAM"]["definition"], words["AABAM"]["suggestion"]) == (0.0, None, "likely_delete")


def test_inflected_forms_are_grouped_with_their_lemma(dela_file, lexique_file, wiktionary_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"

    build_lexicon(dela_file, lexique_file, db_path, wiktionary_file, log=lambda _: None)

    words = fetch_words(db_path)
    # Absent de Lexique : le lemme vient du Wiktionnaire (« forme de ouvrager »)
    assert (words["OUVRAGEAMES"]["lemma"], words["OUVRAGEAMES"]["lemma_norm"]) == ("ouvrager", "OUVRAGER")
    assert words["PORTES"]["lemma_norm"] == "PORTE"


def test_queue_order_puts_short_rare_words_first(dela_file, lexique_file, wiktionary_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"

    build_lexicon(dela_file, lexique_file, db_path, wiktionary_file, log=lambda _: None)

    ordered = sorted(fetch_words(db_path).values(), key=lambda w: w["queue_order"])
    assert [w["norm"] for w in ordered] == [
        "ETE", "AABAM", "PORTE", "PORTES", "OUVRAGE", "APRIORI", "OUVRAGER", "OUVRAGEAMES",
    ]


def test_build_records_sources_and_thresholds(dela_file, lexique_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"

    build_lexicon(dela_file, lexique_file, db_path, log=lambda _: None)

    connection = sqlite3.connect(db_path)
    meta = dict(connection.execute("SELECT key, value FROM meta"))
    connection.close()
    sources = json.loads(meta["sources"])
    assert set(sources) == {"dela", "lexique"}
    assert len(sources["lexique"]["sha256"]) == 64
    assert json.loads(meta["thresholds"])["auto_keep_zipf"] == 3.5


def test_build_without_wiktionary_has_no_definitions(dela_file, lexique_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"

    stats = build_lexicon(dela_file, lexique_file, db_path, log=lambda _: None)

    assert stats.with_definition == 0
    assert fetch_words(db_path)["OUVRAGER"]["suggestion"] == "likely_delete"


def test_rebuild_replaces_the_previous_database(dela_file, lexique_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela_file, lexique_file, db_path, log=lambda _: None)

    build_lexicon(dela_file, lexique_file, db_path, log=lambda _: None)

    assert len(fetch_words(db_path)) == 8
    assert not db_path.with_suffix(".tmp").exists()
