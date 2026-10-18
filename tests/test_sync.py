import fetch_garmin
import fetch_strava
import pytest
import sync
import tokens


def fail(*args):
    raise ConnectionError("Garmin said no")


def test_auto_falls_back_to_strava(monkeypatch, capsys):
    monkeypatch.setattr(fetch_garmin, "fetch", fail)
    monkeypatch.setattr(fetch_strava, "configured", lambda: True)
    monkeypatch.setattr(fetch_strava, "fetch", lambda since, token: (["from strava"], "new-refresh"))
    cache = {"garmin": "old"}

    assert sync.fetch("auto", None, cache) == ["from strava"]
    assert cache == {"garmin": "old", "strava": "new-refresh"}
    assert "::warning::Garmin failed" in capsys.readouterr().out


def test_failure_is_loud_without_fallback(monkeypatch):
    monkeypatch.setattr(fetch_garmin, "fetch", fail)
    monkeypatch.setattr(fetch_strava, "configured", lambda: False)
    with pytest.raises(ConnectionError):
        sync.fetch("auto", None, {})
    monkeypatch.setattr(fetch_strava, "configured", lambda: True)
    with pytest.raises(ConnectionError):
        sync.fetch("garmin", None, {})


def test_garmin_token_is_kept(monkeypatch):
    monkeypatch.setattr(fetch_garmin, "fetch", lambda since, token: (["a"], token + "+refreshed"))
    cache = {"garmin": "tok"}
    assert sync.fetch("auto", None, cache) == ["a"]
    assert cache["garmin"] == "tok+refreshed"


def test_token_cache_roundtrip(tmp_path):
    path = tmp_path / ".tokens" / "tokens.enc"
    tokens.save({"garmin": "secret-token"}, "key", path)
    assert b"secret-token" not in path.read_bytes()
    assert tokens.load("key", path) == {"garmin": "secret-token"}
    assert tokens.load("wrong key", path) == {}
    assert tokens.load(None, path) == {}

    tokens.save({"garmin": "x"}, None, tmp_path / "unused.enc")
    assert not (tmp_path / "unused.enc").exists()
