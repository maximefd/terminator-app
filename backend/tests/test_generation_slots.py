"""Places de génération (ADR 0013) : au plus N générations à la fois, une seule par visiteur."""

import pytest

from generation_slots import GenerationBusy, generation_slot


def test_a_visitor_cannot_run_two_generations_at_once(tmp_path):
    with generation_slot(str(tmp_path), "ip:203.0.113.1", max_concurrent=2):
        with pytest.raises(GenerationBusy) as busy:
            with generation_slot(str(tmp_path), "ip:203.0.113.1", max_concurrent=2):
                pass

    assert busy.value.reason == "visitor"


def test_the_server_refuses_beyond_its_places(tmp_path):
    with generation_slot(str(tmp_path), "compte:1", max_concurrent=2):
        with generation_slot(str(tmp_path), "compte:2", max_concurrent=2):
            with pytest.raises(GenerationBusy) as busy:
                with generation_slot(str(tmp_path), "compte:3", max_concurrent=2):
                    pass

    assert busy.value.reason == "server"


def test_places_are_given_back_after_the_generation(tmp_path):
    with generation_slot(str(tmp_path), "compte:1", max_concurrent=1):
        pass

    with generation_slot(str(tmp_path), "compte:2", max_concurrent=1):
        pass  # la place du premier est libre


def test_places_are_given_back_when_the_generation_fails(tmp_path):
    with pytest.raises(RuntimeError):
        with generation_slot(str(tmp_path), "compte:1", max_concurrent=1):
            raise RuntimeError("le solveur a planté")

    with generation_slot(str(tmp_path), "compte:1", max_concurrent=1):
        pass


def test_a_refused_visitor_does_not_keep_a_place(tmp_path):
    """Refusé faute de place, le visiteur ne doit pas garder son propre verrou."""
    with generation_slot(str(tmp_path), "compte:1", max_concurrent=1):
        with pytest.raises(GenerationBusy):
            with generation_slot(str(tmp_path), "compte:2", max_concurrent=1):
                pass

    with generation_slot(str(tmp_path), "compte:2", max_concurrent=1):
        pass
