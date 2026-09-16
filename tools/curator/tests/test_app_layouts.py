"""Curateur : éditeur de layouts (écriture dans le catalogue, jamais d'écrasement)."""

import pytest

from tools.curator.app import CSRF_HEADER, create_app

PIN = "246810"
API = {CSRF_HEADER: "1"}
GRID = ["x-x", "---", "---"]


@pytest.fixture
def layouts_dir(tmp_path):
    root = tmp_path / "layouts"
    (root / "3x3").mkdir(parents=True)
    (root / "3x3" / "001.txt").write_text("x-x\n---\n---\n")
    return root


def make_client(tmp_path, layouts_dir):
    # Pas de base du lexique : l'éditeur de layouts doit rester utilisable
    app = create_app(tmp_path / "absent.sqlite", tmp_path / "decisions.csv", PIN, secret_key="test",
                     testing=True, layouts_dir=layouts_dir)
    return app.test_client()


@pytest.fixture
def client(tmp_path, layouts_dir):
    client = make_client(tmp_path, layouts_dir)
    assert client.post("/login", json={"pin": PIN}).status_code == 200
    return client


def folders(layouts_dir):
    return sorted(path.name for path in layouts_dir.iterdir())


def test_starts_without_the_lexicon_database(client):
    assert client.get("/").headers["Location"].endswith("/layouts")
    assert client.get("/layouts").status_code == 200
    response = client.get("/api/queue")
    assert response.status_code == 503
    assert "make lexicon-build" in response.get_json()["error"]


def test_layouts_require_the_pin(tmp_path, layouts_dir):
    anonymous = make_client(tmp_path, layouts_dir)

    assert anonymous.get("/layouts").headers["Location"].endswith("/login")
    assert anonymous.get("/static/layouts.js").status_code == 302
    assert anonymous.get("/api/layouts").status_code == 401
    assert anonymous.post("/api/layouts", json={"rows": ["x--", "---", "---"]}, headers=API).status_code == 401
    assert folders(layouts_dir) == ["3x3"]


def test_catalog_lists_existing_layouts(client):
    layout = client.get("/api/layouts").get_json()["formats"][0]["layouts"][0]

    assert (layout["id"], layout["rows"]) == ("3x3-001", GRID)


def test_check_reports_errors_duplicates_and_the_next_id(client):
    new = client.post("/api/layouts/check", json={"rows": ["x--", "---", "---"]}, headers=API).get_json()
    assert new["valid"] and new["duplicate_of"] is None and new["next_id"] == "3x3-002"

    existing = client.post("/api/layouts/check", json={"rows": GRID}, headers=API).get_json()
    assert existing["duplicate_of"] == "3x3-001"

    broken = client.post("/api/layouts/check", json={"rows": ["x-", "-x"]}, headers=API).get_json()
    assert not broken["valid"] and broken["next_id"] is None
    assert broken["errors"][0]["cells"] == [[1, 0]]


def test_save_writes_the_next_file_without_touching_the_others(client, layouts_dir):
    response = client.post("/api/layouts", json={"rows": ["x--", "---", "---"]}, headers=API)

    assert response.status_code == 201
    assert response.get_json()["id"] == "3x3-002"
    assert (layouts_dir / "3x3" / "002.txt").read_text() == "x--\n---\n---\n"
    assert (layouts_dir / "3x3" / "001.txt").read_text() == "x-x\n---\n---\n"


def test_save_creates_a_new_format_folder(client, layouts_dir):
    response = client.post("/api/layouts", json={"rows": ["x----", "-----"]}, headers=API)

    assert response.get_json()["id"] == "5x2-001"
    assert folders(layouts_dir) == ["3x3", "5x2"]


def test_save_refuses_duplicates_and_invalid_grids(client, layouts_dir):
    duplicate = client.post("/api/layouts", json={"rows": GRID}, headers=API)
    assert duplicate.status_code == 409
    assert duplicate.get_json()["duplicate_of"] == "3x3-001"

    invalid = client.post("/api/layouts", json={"rows": ["x-", "-x"]}, headers=API)
    assert invalid.status_code == 400
    assert invalid.get_json()["report"]["errors"]

    assert folders(layouts_dir) == ["3x3"]
    assert [path.name for path in (layouts_dir / "3x3").iterdir()] == ["001.txt"]


@pytest.mark.parametrize("body", [
    {},
    {"rows": "x--"},
    {"rows": []},
    {"rows": [1, 2]},
    {"rows": ["-" * 31, "-" * 31]},
    {"rows": ["../../etc", "---------"]},
])
def test_malformed_grids_are_rejected(client, layouts_dir, body):
    assert client.post("/api/layouts", json=body, headers=API).status_code == 400
    assert folders(layouts_dir) == ["3x3"]


def test_save_requires_the_csrf_header(client, layouts_dir):
    assert client.post("/api/layouts", json={"rows": ["x--", "---", "---"]}).status_code == 403
    assert [path.name for path in (layouts_dir / "3x3").iterdir()] == ["001.txt"]
