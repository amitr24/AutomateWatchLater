from datetime import datetime, timedelta, timezone
from pathlib import Path

from watchlater.domain import Video, rank_video
from watchlater.inbox import load_videos, recommend
from watchlater.store import VideoStore


def video(video_id: str, **overrides) -> Video:
    values = {
        "video_id": video_id,
        "title": f"Video {video_id}",
        "channel": "Example",
        "duration_seconds": 600,
        "added_at": datetime.now(timezone.utc) - timedelta(days=10),
        "category": "machine-learning",
        "priority": 3,
    }
    values.update(overrides)
    return Video(**values)


def test_ranker_rewards_fit_and_priority():
    high = rank_video(video("high", priority=5), available_seconds=900)
    low = rank_video(video("low", priority=1), available_seconds=900)
    too_long = rank_video(
        video("long", priority=5, duration_seconds=3600), available_seconds=900
    )
    assert high.score > low.score
    assert high.score > too_long.score
    assert "fits 15-minute budget" in high.reasons


def test_store_is_idempotent_and_tracks_completion(tmp_path):
    database = tmp_path / "inbox.db"
    with VideoStore(database) as store:
        assert store.upsert([video("abc")]) == 1
        assert store.upsert([video("abc", title="Updated")]) == 1
        assert store.stats()["total"] == 1
        assert store.complete("abc")
        assert not store.complete("abc")
        assert store.stats()["completed"] == 1


def test_recommendations_are_deterministic(tmp_path):
    with VideoStore(tmp_path / "inbox.db") as store:
        store.upsert([video("b"), video("a")])
        assert [item.video.video_id for item in recommend(
            store, available_minutes=20
        )] == ["a", "b"]


def test_csv_import(tmp_path):
    source = tmp_path / "videos.csv"
    source.write_text(
        "video_id,title,channel,duration_seconds,added_at,category,priority\n"
        "x1,Calibration Explained,ML Lab,720,2026-01-01T00:00:00Z,ml,5\n",
        encoding="utf-8",
    )
    assert load_videos(source)[0].video_id == "x1"
