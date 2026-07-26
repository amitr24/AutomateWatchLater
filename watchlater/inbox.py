"""Application services for importing and recommending videos."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from .domain import RankedVideo, Video, rank_video
from .store import VideoStore


def load_videos(path: Path) -> list[Video]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            records = list(csv.DictReader(handle))
    elif path.suffix.lower() in {".jsonl", ".ndjson"}:
        with path.open(encoding="utf-8") as handle:
            records = [json.loads(line) for line in handle if line.strip()]
    else:
        raise ValueError("Input must be CSV or JSONL")
    return [_parse_video(record) for record in records]


def recommend(
    store: VideoStore, *, available_minutes: int, limit: int = 5
) -> list[RankedVideo]:
    pending = store.pending()
    category_counts = Counter(video.category for video in pending)
    ranked = [
        rank_video(
            video,
            available_seconds=available_minutes * 60,
            category_count=category_counts[video.category] - 1,
        )
        for video in pending
    ]
    return sorted(ranked, key=lambda item: (-item.score, item.video.video_id))[:limit]


def _parse_video(record: dict[str, str]) -> Video:
    required = ("video_id", "title", "channel", "duration_seconds", "added_at")
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return Video(
        video_id=record["video_id"].strip(),
        title=record["title"].strip(),
        channel=record["channel"].strip(),
        duration_seconds=int(record["duration_seconds"]),
        added_at=datetime.fromisoformat(record["added_at"].replace("Z", "+00:00")),
        category=(record.get("category") or "uncategorized").strip(),
        priority=int(record.get("priority") or 3),
    )
