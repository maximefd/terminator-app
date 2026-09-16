"""Mots obligatoires : refus expliqués avant toute résolution, et layouts de repli (#18, ADR 0007)."""

from engine.must_words import check_must_words, slot_lengths
from layout_catalog import suggest_layouts_for


def slots(*lengths):
    return [{"id": i, "x": 0, "y": i, "direction": "across", "length": length}
            for i, length in enumerate(lengths)]


def words_refused(problems):
    return [problem["word"] for problem in problems]


def test_slot_lengths_counts_the_places_of_each_size():
    assert slot_lengths(slots(3, 5, 3)) == {3: 2, 5: 1}


def test_words_that_fit_raise_nothing():
    assert check_must_words(slots(3, 5, 5), ["ABC", "PORTE"]) == []


def test_a_word_longer_than_every_place_is_refused():
    problems = check_must_words(slots(3, 5), ["ANTICONSTITUTIONNEL"])

    assert words_refused(problems) == ["ANTICONSTITUTIONNEL"]
    assert "19 lettres" in problems[0]["problem"] and "5" in problems[0]["problem"]


def test_more_words_of_one_length_than_places_of_that_length():
    problems = check_must_words(slots(5, 3, 3), ["PORTE", "ROUTE"])

    # Un seul emplacement de 5 lettres pour deux mots : les deux sont concernés, chacun a son explication
    assert words_refused(problems) == ["PORTE", "ROUTE"]
    assert all("2 mots de 5 lettres" in problem["problem"] for problem in problems)


def test_a_layout_without_any_place_of_that_length():
    # 4 lettres : plus court que le plus long emplacement (5), mais aucun emplacement de cette taille
    problems = check_must_words(slots(3, 5), ["PORT"])

    assert words_refused(problems) == ["PORT"]
    assert "0 emplacement(s)" in problems[0]["problem"]


def catalog_dir(tmp_path):
    (tmp_path / "3x3").mkdir()
    (tmp_path / "3x3" / "001.txt").write_text("x-x\n---\n---\n", encoding="utf-8")
    return str(tmp_path)


def test_suggested_layouts_are_those_where_the_words_fit(tmp_path):
    layouts_dir = catalog_dir(tmp_path)

    assert suggest_layouts_for(["ABC"], layouts_dir) == ["3x3-001"]
    assert suggest_layouts_for(["ABC", "DEF", "GHI"], layouts_dir) == ["3x3-001"]  # 3 emplacements de 3
    assert suggest_layouts_for(["ABCD"], layouts_dir) == []  # aucun emplacement de 4 lettres
    assert suggest_layouts_for(["ABC"] * 4, layouts_dir) == []  # 4 mots pour 3 emplacements
