"""Domain models and an explainable ranking policy."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    channel: str
    duration_seconds: int
    added_at: datetime
    category: str = "uncategorized"
    priority: int = 3
    completed_at: datetime | None = None


@dataclass(frozen=True)
class RankedVideo:
    video: Video
    score: float
    reasons: tuple[str, ...]


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def rank_video(
    video: Video,
    *,
    available_seconds: int,
    now: datetime | None = None,
    category_count: int = 0,
) -> RankedVideo:
    """Score one video using inspectable features rather than a black box."""
    if video.completed_at is not None:
        return RankedVideo(video, float("-inf"), ("already completed",))

    now = _utc(now or datetime.now(timezone.utc))
    age_days = max(0.0, (now - _utc(video.added_at)).total_seconds() / 86_400)
    age_score = min(math.log1p(age_days) / math.log(31), 1.0)
    priority_score = (min(max(video.priority, 1), 5) - 1) / 4
    fits = video.duration_seconds <= available_seconds
    fit_score = 1.0 if fits else -min(
        (video.duration_seconds - available_seconds) / max(available_seconds, 1),
        1.0,
    )
    diversity_score = 1 / (1 + max(category_count, 0))

    score = (
        0.35 * priority_score
        + 0.30 * fit_score
        + 0.20 * age_score
        + 0.15 * diversity_score
    )
    reasons = (
        f"priority {video.priority}/5",
        f"{'fits' if fits else 'exceeds'} {available_seconds // 60}-minute budget",
        f"waiting {age_days:.0f} days",
        f"category exposure {category_count}",
    )
    return RankedVideo(video, round(score, 6), reasons)
