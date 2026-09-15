import os
import threading

from lexicon_loader import LexiconManager


def write_lexicon(path, words):
    path.write_text("".join(f"{word};{word.lower()};Définition\n" for word in words), encoding="utf-8")


def touch_later(path, seconds=2):
    """Garantit un horodatage différent, même sur un système de fichiers peu précis."""
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + seconds * 1_000_000_000))


def test_uses_the_curated_lexicon_when_it_exists(tmp_path):
    curated, fallback = tmp_path / "lexique_cure.csv", tmp_path / "dela.csv"
    write_lexicon(curated, ["PORTE", "CHAT"])
    write_lexicon(fallback, ["PORTE", "CHAT", "AABAM"])
    manager = LexiconManager(curated, fallback)

    assert manager.check()

    assert manager.trie.words == {"PORTE", "CHAT"}
    assert (manager.info.source, manager.info.curated, manager.info.words) == ("lexique_cure.csv", True, 2)


def test_falls_back_to_the_full_dela_when_nothing_is_exported(tmp_path):
    fallback = tmp_path / "dela.csv"
    write_lexicon(fallback, ["PORTE", "AABAM"])
    manager = LexiconManager(tmp_path / "absent.csv", fallback)

    manager.check()

    assert manager.info.curated is False
    assert "AABAM" in manager.trie.words


def test_reloads_only_when_the_file_changes(tmp_path):
    curated, fallback = tmp_path / "lexique_cure.csv", tmp_path / "dela.csv"
    write_lexicon(curated, ["PORTE", "AABAM"])
    write_lexicon(fallback, ["PORTE"])
    manager = LexiconManager(curated, fallback)
    manager.check()
    first_trie = manager.trie

    assert manager.check() is False
    assert manager.trie is first_trie

    write_lexicon(curated, ["PORTE"])  # l'auteur a supprimé AABAM
    touch_later(curated)

    assert manager.check() is True
    assert manager.trie.words == {"PORTE"}


def test_switches_to_the_curated_lexicon_once_exported(tmp_path):
    curated, fallback = tmp_path / "lexique_cure.csv", tmp_path / "dela.csv"
    write_lexicon(fallback, ["PORTE", "AABAM"])
    manager = LexiconManager(curated, fallback)
    manager.check()

    write_lexicon(curated, ["PORTE"])

    assert manager.check() is True
    assert manager.info.curated is True


def test_a_missing_source_keeps_the_current_lexicon(tmp_path):
    fallback = tmp_path / "dela.csv"
    write_lexicon(fallback, ["PORTE"])
    manager = LexiconManager(None, fallback)
    manager.check()

    fallback.unlink()

    assert manager.check() is False
    assert manager.trie.words == {"PORTE"}


def test_watcher_reloads_in_the_background(tmp_path):
    curated, fallback = tmp_path / "lexique_cure.csv", tmp_path / "dela.csv"
    write_lexicon(fallback, ["PORTE", "AABAM"])
    manager = LexiconManager(curated, fallback)
    manager.check()
    reloaded = threading.Event()
    manager.start_watching(0.05, on_reload=lambda _: reloaded.set())

    try:
        write_lexicon(curated, ["PORTE"])
        assert reloaded.wait(timeout=3)
        assert manager.trie.words == {"PORTE"}
    finally:
        manager.stop()


def test_status_reports_the_loaded_lexicon(test_app, client, monkeypatch, tmp_path):
    curated = tmp_path / "lexique_cure.csv"
    write_lexicon(curated, ["PORTE", "CHAT"])
    manager = LexiconManager(curated, tmp_path / "dela.csv")
    manager.check()
    monkeypatch.setattr(test_app, "lexicon", manager, raising=False)
    monkeypatch.setattr(test_app, "dela_trie", manager.trie)

    status = client.get("/api/status").get_json()

    assert status["word_count"] == 2
    assert status["lexicon"]["source"] == "lexique_cure.csv"
    assert status["lexicon"]["curated"] is True
