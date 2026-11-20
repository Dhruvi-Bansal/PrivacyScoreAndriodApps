"""API and parity tests.  Run from rl_privacy_app/:  python -m pytest backend/tests -q"""
import pytest
from fastapi.testclient import TestClient

from backend.app import playstore
from backend.app.main import app, registry

client = TestClient(app)
CATEGORIES = registry.available()
pytestmark = pytest.mark.skipif(not CATEGORIES, reason="no exported models; run export_models.py first")


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_categories_listed():
    cats = client.get("/api/categories").json()
    assert {c["key"] for c in cats} == set(CATEGORIES)
    for c in cats:
        assert len(c["permissions"]) == 12 and 0 < c["threshold"] < 1


@pytest.mark.parametrize("key", CATEGORIES)
def test_matches_notebook_on_test_examples(key):
    """The API reproduces the notebook's decisions and privacy score for real test-set apps."""
    for ex in registry.config(key)["examples"]:
        body = {k: v for k, v in ex.items() if k not in ("notebook", "true_label")} | {"category": key}
        res = client.post("/api/analyze", json=body).json()["result"]
        nb = ex["notebook"]
        assert res["privacy_score"] == pytest.approx(nb["privacy_score"], abs=0.02), ex["app_name"]
        assert (res["verdict"] == "malicious") == nb["malicious"], ex["app_name"]
        assert ";".join(sorted(res["allowed"])) == nb["allowed"], ex["app_name"]


def test_manual_groups_only():
    res = client.post("/api/analyze", json={
        "category": CATEGORIES[0], "app_name": "Test", "description": "free app",
        "permission_groups": ["Internet", "Camera", "SMS"], "rating": 4.2, "num_ratings": 100}).json()["result"]
    assert res["verdict"] in ("malicious", "benign")
    assert {d["permission"] for d in res["decisions"]} <= {"Internet", "Camera", "SMS"}
    assert res["assumed_permissions"], "groups without exact permissions should use a representative permission"


def test_category_from_genre_and_unknown_category():
    genre = registry.config(CATEGORIES[0])["genres"][0]
    assert client.post("/api/analyze", json={"genre": genre}).status_code == 200
    assert client.post("/api/analyze", json={"category": "nope"}).status_code == 422
    assert client.post("/api/analyze", json={}).status_code == 422


def test_unrecognised_permission_is_reported():
    res = client.post("/api/analyze", json={"category": CATEGORIES[0], "permissions": ["made up permission"]}).json()
    assert res["result"]["unrecognized_permissions"] == ["made up permission"]


def test_extract_package_id():
    assert playstore.extract_package_id("https://play.google.com/store/apps/details?id=com.whatsapp&hl=en") == "com.whatsapp"
    assert playstore.extract_package_id("com.spotify.music") == "com.spotify.music"
    for bad in ("https://example.com/?id=com.a.b", "https://play.google.com/store/apps/details", "hello"):
        with pytest.raises(playstore.PlayStoreError):
            playstore.extract_package_id(bad)


def test_bad_link_returns_422():
    r = client.post("/api/analyze-url", json={"url": "https://example.com/app"})
    assert r.status_code == 422 and "Google Play" in r.json()["detail"]


def test_reputation_and_trust():
    big = {"minInstalls": 5_000_000_000, "ratings": 200_000_000, "score": 4.5, "released": "Oct 18, 2010",
           "privacyPolicy": "x", "developerWebsite": "y"}
    new = {"minInstalls": 1000, "ratings": None, "score": None, "released": None}
    assert playstore.reputation(big)["trust"] == pytest.approx(playstore.MAX_TRUST)
    assert playstore.reputation(new)["trust"] < 0.05
    m = registry.get(CATEGORIES[0])
    ex = {k: v for k, v in registry.config(CATEGORIES[0])["examples"][0].items() if k not in ("notebook", "true_label")}
    plain, trusted = m.analyze(dict(ex)), m.analyze(dict(ex), trust=0.8)
    assert trusted["privacy_score"] < plain["privacy_score"]
    assert m.analyze(dict(ex), trust=0.0)["privacy_score"] == plain["privacy_score"]


def test_map_permissions():
    mapped, unmapped = playstore.map_permissions({
        "Camera": ["take pictures and videos"],
        "Location": ["precise location (GPS and network-based)", "approximate location (network-based)"],
        "Other": ["full network access", "install shortcuts"]})
    assert "Hardware controls : take pictures and videos (D)" in mapped
    assert "Your location : fine (GPS) location (D)" in mapped
    assert "Network communication : full Internet access (D)" in mapped
    assert unmapped == ["install shortcuts"]
    cols = set(registry.config(CATEGORIES[0])["raw_permission_columns"])
    assert all(col in cols for _, col in playstore.PERMISSION_RULES), "every mapping target must be a dataset column"
