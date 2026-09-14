import json

import pytest

from tools.lexicon.download import SOURCES, ChecksumMismatch, download_sources


def fake_fetch(content_by_url):
    calls = []

    def fetch(url, destination):
        calls.append(url)
        destination.write_bytes(content_by_url[url])

    fetch.calls = calls
    return fetch


@pytest.fixture
def contents():
    return {source.url: f"contenu de {name}".encode() for name, source in SOURCES.items()}


def test_downloads_missing_sources_and_records_checksums(tmp_path, contents):
    fetch = fake_fetch(contents)
    lock_path = tmp_path / "sources.lock.json"

    lock = download_sources(tmp_path / "raw", lock_path, fetch=fetch, log=lambda _: None)

    assert len(fetch.calls) == len(SOURCES)
    assert json.loads(lock_path.read_text()) == lock
    assert all(len(entry["sha256"]) == 64 for entry in lock.values())
    assert not list((tmp_path / "raw").glob("*.part"))


def test_existing_sources_are_verified_not_downloaded(tmp_path, contents):
    lock_path = tmp_path / "sources.lock.json"
    download_sources(tmp_path / "raw", lock_path, fetch=fake_fetch(contents), log=lambda _: None)
    fetch = fake_fetch(contents)

    download_sources(tmp_path / "raw", lock_path, fetch=fetch, log=lambda _: None)

    assert fetch.calls == []


def test_modified_source_is_detected(tmp_path, contents):
    lock_path = tmp_path / "sources.lock.json"
    download_sources(tmp_path / "raw", lock_path, fetch=fake_fetch(contents), log=lambda _: None)
    (tmp_path / "raw" / SOURCES["lexique"].filename).write_bytes(b"modifie")

    with pytest.raises(ChecksumMismatch):
        download_sources(tmp_path / "raw", lock_path, fetch=fake_fetch(contents), log=lambda _: None)


def test_refresh_downloads_again_and_updates_the_lock(tmp_path, contents):
    lock_path = tmp_path / "sources.lock.json"
    first = download_sources(tmp_path / "raw", lock_path, fetch=fake_fetch(contents), log=lambda _: None)
    updated = {url: data + b" v2" for url, data in contents.items()}

    second = download_sources(tmp_path / "raw", lock_path, refresh=True, fetch=fake_fetch(updated), log=lambda _: None)

    assert second["lexique"]["sha256"] != first["lexique"]["sha256"]
