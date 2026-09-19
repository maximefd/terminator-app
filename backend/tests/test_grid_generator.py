import os

import pytest

from engine.grid_solver import GridSolver
from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from grid_generator import GridGenerator, LayoutNotFoundError, crossing_load, luby
from layout_catalog import DEFAULT_LAYOUTS_DIR, available_formats, layout_id
from tests.paths import FIXTURE_LAYOUTS_DIR
from trie_engine import DictionnaireTrie


def test_available_formats_lists_only_formats_with_layouts(tmp_path):
    (tmp_path / "6x7").mkdir()
    (tmp_path / "6x7" / "a.txt").write_text("..")
    (tmp_path / "11x6").mkdir()
    (tmp_path / "11x6" / "a.txt").write_text("..")
    (tmp_path / "11x6" / "b.txt").write_text("..")
    (tmp_path / "9x9").mkdir()  # dossier vide : ignoré
    (tmp_path / "notes").mkdir()  # nom invalide : ignoré
    (tmp_path / "notes" / "a.txt").write_text("")

    assert available_formats(str(tmp_path)) == [
        {"width": 6, "height": 7, "layouts": 1},
        {"width": 11, "height": 6, "layouts": 2},
    ]


def test_available_formats_on_missing_directory(tmp_path):
    assert available_formats(str(tmp_path / "absent")) == []


def test_missing_layout_raises(small_words, small_trie):
    with pytest.raises(LayoutNotFoundError):
        GridGenerator(9, 9, small_words, prebuilt_trie=small_trie, layouts_dir=FIXTURE_LAYOUTS_DIR)


def test_layout_id_is_derived_from_the_path():
    assert layout_id(os.path.join("layouts", "11x6", "007.txt")) == "11x6-007"


def test_shipped_layouts_load_regardless_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    formats = available_formats()

    assert {(6, 7), (11, 6)} <= {(f["width"], f["height"]) for f in formats}
    for fmt in formats:
        format_dir = os.path.join(DEFAULT_LAYOUTS_DIR, f"{fmt['width']}x{fmt['height']}")
        for name in os.listdir(format_dir):
            template = GridTemplate(fmt["width"], fmt["height"], os.path.join(format_dir, name))
            assert SlotFinder(template).find_all_slots(), f"{name} ne contient aucun slot"


def test_luby_sequence():
    assert [luby(i) for i in range(1, 16)] == [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]


def make_generator(small_words, small_trie, **kwargs):
    return GridGenerator(5, 5, small_words, prebuilt_trie=small_trie, layouts_dir=FIXTURE_LAYOUTS_DIR, **kwargs)


def test_restarts_find_a_grid_and_stay_deterministic(small_words, small_trie):
    results = []
    for _ in range(2):
        generator = make_generator(small_words, small_trie, seed=3, restart_unit_calls=1)
        assert generator.generate()
        results.append(generator.get_grid_data())

    assert results[0]["cells"] == results[1]["cells"]
    assert results[0]["statistics"]["attempts"] > 1


def test_interrupted_attempt_gives_back_the_words_it_used(small_words, small_trie):
    generator = make_generator(small_words, small_trie, seed=3, restart_unit_calls=None)
    sizes = {length: len(words) for length, words in generator.repository.words_by_len.items()}
    # Un seul appel : le premier mot est placé, puis l'essai s'arrête (le 5×5 se remplit en quelques appels)
    generator.solver.max_recursive_calls = 1

    assert not generator.generate()
    assert generator.solver.stop_reason == "calls"
    assert not generator.budget_exceeded  # seuil d'appels, pas le budget temps
    assert {length: len(words) for length, words in generator.repository.words_by_len.items()} == sizes


def test_time_budget_stops_the_restarts(small_words, small_trie):
    generator = make_generator(small_words, small_trie, seed=3, time_budget_s=-1, restart_unit_calls=1)

    assert not generator.generate()
    assert generator.budget_exceeded
    assert len(generator.attempts) == 1


def test_grid_data_shape(small_words, small_trie):
    generator = GridGenerator(5, 5, small_words, prebuilt_trie=small_trie, layouts_dir=FIXTURE_LAYOUTS_DIR, seed=3)
    assert generator.generate()

    data = generator.get_grid_data()

    assert (data["width"], data["height"], data["seed"]) == (5, 5, 3)
    assert data["layout"] == "5x5-001"
    assert len(data["cells"]) == 25
    assert {"metrics", "cache_stats", "placement_history"} <= data["statistics"].keys()


def test_a_must_word_is_placed_and_reported_as_such(small_words, small_trie):
    # Le mot imposé est repris d'une grille déjà résolue avec ce seed : une solution existe forcément
    reference = make_generator(small_words, small_trie, seed=3)
    assert reference.generate()
    imposed = reference.get_grid_data()["words"][0]["text"]

    generator = make_generator(small_words, small_trie, seed=3, must_words=[imposed], time_budget_s=20)

    assert generator.generate()
    data = generator.get_grid_data()
    assert data["must_words"] == [imposed]
    assert generator.unplaced_must_words == []
    assert [word["source"] for word in data["words"] if word["text"] == imposed] == ["must"]
    assert data["wish_ratio"] > 0  # le mot imposé compte dans la part des mots de l'auteur


def test_an_impossible_must_word_is_named_after_the_failure(small_trie):
    # Sans lexique commun, le mot imposé est seul : sa longueur convient au layout, mais rien ne peut
    # le croiser. (Avec les 11 600 mots de la fixture, « ZZZZZ » se croise très bien : HADZA, NAZI, SEIZE…)
    generator = GridGenerator(5, 5, [], prebuilt_trie=small_trie, layouts_dir=FIXTURE_LAYOUTS_DIR,
                              seed=3, must_words=["ZZZZZ"], restart_unit_calls=None)

    assert not generator.generate()
    assert generator.unplaced_must_words == ["ZZZZZ"]


def test_the_forward_checking_threshold_reaches_the_solver(small_words, small_trie):
    """Réglable pour les mesures (#61) ; sans réglage, le solveur applique son minimum."""
    default = make_generator(small_words, small_trie, seed=3)
    tuned = make_generator(small_words, small_trie, seed=3, min_safe_candidates=5)

    assert default.solver.min_safe_candidates == GridSolver.MIN_SAFE_CANDIDATES == 2
    assert tuned.solver.min_safe_candidates == 5


def charge_de(rows, length):
    template = GridTemplate.from_rows(rows)
    finder = SlotFinder(template)
    finder.find_all_slots()
    return crossing_load(finder, length)


def test_crossing_load_measures_how_constrained_a_word_would_be():
    """Critère du classement des layouts : mesuré (#73), il sépare les layouts qui accueillent un
    mot long de ceux qui le refusent."""
    assert charge_de(["---"], 3) == 0.0  # une seule rangée : aucune lettre à croiser
    assert charge_de(["---", "---", "---"], 3) == 1.0  # chaque lettre est croisée
    assert charge_de(["---"], 5) is None  # aucun emplacement de cette longueur


# --- Choix du layout quand des mots sont imposés (#73) ---

# Deux layouts 3x3 aux géométries incompatibles : l'un n'a que des emplacements de 3 lettres,
# l'autre que des emplacements de 2. Un mot imposé ne peut donc entrer que dans l'un des deux.
LAYOUT_DE_TROIS = "---\n---\n---\n"
LAYOUT_DE_DEUX = "--x\n--x\nxxx\n"


def two_layouts(tmp_path):
    (tmp_path / "3x3").mkdir(parents=True)
    (tmp_path / "3x3" / "001.txt").write_text(LAYOUT_DE_TROIS, encoding="utf-8")
    (tmp_path / "3x3" / "002.txt").write_text(LAYOUT_DE_DEUX, encoding="utf-8")
    return str(tmp_path)


def tiny_trie(*words):
    trie = DictionnaireTrie()
    for word in words:
        trie.insert(word)
    return trie


def generator_3x3(tmp_path, **kwargs):
    trie = tiny_trie("ABC", "DEF", "AD", "BE", "CF")
    return GridGenerator(3, 3, ["ABC", "DEF", "AD", "BE", "CF"], prebuilt_trie=trie,
                         layouts_dir=two_layouts(tmp_path), seed=1, **kwargs)


def test_without_imposed_words_a_single_layout_is_drawn(tmp_path):
    """Comportement d'origine préservé : la baseline doit rester comparable."""
    generator = generator_3x3(tmp_path)

    assert len(generator._layouts) == 1


def test_only_the_layouts_that_host_the_word_are_kept(tmp_path):
    """La vérification porte sur tous les candidats : un mot refusé ici peut entrer là."""
    trois = generator_3x3(tmp_path / "a", must_words=["ABC"])
    deux = generator_3x3(tmp_path / "b", must_words=["AD"])

    assert [path.endswith("001.txt") for path, _, _ in trois._layouts] == [True]
    assert [path.endswith("002.txt") for path, _, _ in deux._layouts] == [True]
    assert trois.must_word_problems == [] and deux.must_word_problems == []


def test_a_word_that_fits_no_layout_is_explained_without_searching(tmp_path):
    generator = generator_3x3(tmp_path, must_words=["ABCD"])

    assert not generator.generate()
    assert generator.must_word_problems
    assert generator.must_word_problems[0]["word"] == "ABCD"
    assert generator.attempts == []  # aucune résolution lancée


def test_generate_really_tries_the_other_layouts(tmp_path):
    """Le test doit passer par generate() : la rotation savait tourner, mais la boucle sortait avant.

    Un mot imposé introuvable épuise la recherche (`stop_reason` à None) au lieu d'atteindre le seuil
    d'appels ; la condition de sortie renvoyait alors la main sans jamais changer de géométrie.
    """
    (tmp_path / "3x3").mkdir()
    (tmp_path / "3x3" / "001.txt").write_text(LAYOUT_DE_TROIS, encoding="utf-8")
    (tmp_path / "3x3" / "002.txt").write_text("x-x\n---\n---\n", encoding="utf-8")
    mots = ["ABC", "DEF", "AD", "BE", "CF"]
    generator = GridGenerator(3, 3, mots, prebuilt_trie=tiny_trie(*mots), layouts_dir=str(tmp_path),
                              seed=1, must_words=["ZZZ"], time_budget_s=5)

    assert len(generator._layouts) == 2
    assert not generator.generate()  # « ZZZ » ne se croise nulle part
    assert len({essai["layout"] for essai in generator.attempts}) == 2


def test_a_single_layout_keeps_the_previous_stop_condition(small_words, small_trie):
    """Sans autre géométrie à essayer, la boucle s'arrête comme avant : la baseline reste comparable."""
    generator = make_generator(small_words, small_trie, seed=3, restart_unit_calls=None)
    generator.solver.max_recursive_calls = 1

    assert not generator.generate()
    assert len(generator.attempts) == 1


def test_each_placed_word_reports_its_pool(small_words, small_trie):
    generator = GridGenerator(5, 5, small_words, prebuilt_trie=small_trie,
                              layouts_dir=FIXTURE_LAYOUTS_DIR, seed=3)
    assert generator.generate()

    data = generator.get_grid_data()

    # Sans mots de l'auteur, tout vient du lexique commun : la part souhaitée est nulle
    assert {word["source"] for word in data["words"]} == {"common"}
    assert data["wish_ratio"] == 0.0
