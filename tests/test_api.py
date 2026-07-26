from datetime import datetime, timezone

from fastapi.testclient import TestClient

from watchlater.api import create_app


def test_health():
    client = TestClient(create_app())
    assert client.get("/api/health").json() == {"status": "ok"}


def test_video_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setenv("WATCHLATER_DATABASE", str(tmp_path / "api.db"))
    client = TestClient(create_app())
    payload = {
        "video_id": "test123",
        "title": "Reliable ranking systems",
        "channel": "Systems Lab",
        "duration_seconds": 900,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "category": "machine-learning",
        "priority": 5,
    }
    assert client.post("/api/videos", json=payload).status_code == 201
    recommendations = client.get(
        "/api/recommendations", params={"minutes": 20}
    ).json()
    assert recommendations[0]["video_id"] == "test123"
    assert recommendations[0]["reasons"]
    assert client.post("/api/videos/test123/complete").status_code == 200
    assert client.get("/api/stats").json()["completed"] == 1
