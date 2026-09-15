import pytest

from tools.curator.exporter import LexiconExporter


class FakeExport:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def __call__(self, db_path, decisions_path, out_path):
        self.calls += 1
        if self.fail:
            raise OSError("disque plein")
        return {"exported": 700_000, "deleted_by_author": 1_234}


def make_exporter(tmp_path, export, every=500):
    return LexiconExporter(tmp_path / "db", tmp_path / "decisions.csv", tmp_path / "out.csv",
                           every=every, export=export, background=False)


def test_exports_each_time_a_new_milestone_is_crossed(tmp_path):
    export = FakeExport()
    exporter = make_exporter(tmp_path, export)
    exporter.prime(480)

    assert exporter.observe(499) is False
    assert exporter.observe(500) is True
    assert exporter.observe(730) is False
    assert exporter.observe(1_003) is True  # une suppression par famille peut sauter un palier exact
    assert export.calls == 2


def test_no_export_at_startup(tmp_path):
    export = FakeExport()
    exporter = make_exporter(tmp_path, export)

    exporter.prime(1_200)

    assert exporter.observe(1_200) is False
    assert export.calls == 0
    assert exporter.snapshot()["next_at"] == 1_500


def test_status_after_a_successful_export(tmp_path):
    exporter = make_exporter(tmp_path, FakeExport())
    exporter.prime(0)

    exporter.observe(500)

    status = exporter.snapshot()
    assert (status["state"], status["words"], status["deleted"], status["decided_at_export"]) == ("done", 700_000, 1_234, 500)
    assert status["exported_at"]
    assert (status["every"], status["next_at"]) == (500, 1_000)


def test_manual_export(tmp_path):
    export = FakeExport()
    exporter = make_exporter(tmp_path, export)
    exporter.prime(42)

    assert exporter.start(42) is True
    assert export.calls == 1


def test_failures_are_reported(tmp_path):
    exporter = make_exporter(tmp_path, FakeExport(fail=True))
    exporter.prime(0)

    exporter.observe(500)

    status = exporter.snapshot()
    assert status["state"] == "error"
    assert "échoué" in status["error"]


def test_invalid_interval_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        make_exporter(tmp_path, FakeExport(), every=0)
