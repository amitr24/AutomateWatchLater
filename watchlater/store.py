"""SQLite persistence for the local-first video inbox."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from .domain import Video


class VideoStore:
    def __init__(self, path: Path, *, initialize: bool = True) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # FastAPI may enter and finalize a synchronous dependency on different
        # worker threads. Each request still receives its own connection.
        self.connection = sqlite3.connect(
            path, timeout=10, check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 10000")
        self.connection.execute("PRAGMA foreign_keys = ON")
        if initialize:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL CHECK(duration_seconds > 0),
                    added_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 5),
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL REFERENCES videos(video_id),
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                """
            )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "VideoStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def upsert(self, videos: Iterable[Video]) -> int:
        rows = [
            (
                item.video_id,
                item.title,
                item.channel,
                item.duration_seconds,
                item.added_at.isoformat(),
                item.category,
                item.priority,
                item.completed_at.isoformat() if item.completed_at else None,
            )
            for item in videos
        ]
        self.connection.executemany(
            """
            INSERT INTO videos VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
              title=excluded.title, channel=excluded.channel,
              duration_seconds=excluded.duration_seconds,
              category=excluded.category, priority=excluded.priority
            """,
            rows,
        )
        self.connection.commit()
        return len(rows)

    def pending(self) -> list[Video]:
        return [self._video(row) for row in self.connection.execute(
            "SELECT * FROM videos WHERE completed_at IS NULL ORDER BY added_at"
        )]

    def complete(self, video_id: str, when: datetime | None = None) -> bool:
        occurred = (when or datetime.now(timezone.utc)).isoformat()
        cursor = self.connection.execute(
            "UPDATE videos SET completed_at=? WHERE video_id=? AND completed_at IS NULL",
            (occurred, video_id),
        )
        if cursor.rowcount:
            self.connection.execute(
                "INSERT INTO events(video_id,event_type,occurred_at) VALUES (?,?,?)",
                (video_id, "completed", occurred),
            )
        self.connection.commit()
        return bool(cursor.rowcount)

    def stats(self) -> dict[str, object]:
        row = self.connection.execute(
            """
            SELECT COUNT(*) total,
              SUM(CASE WHEN completed_at IS NULL THEN 1 ELSE 0 END) pending,
              SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) completed,
              COALESCE(SUM(CASE WHEN completed_at IS NULL THEN duration_seconds ELSE 0 END),0)
                pending_seconds
            FROM videos
            """
        ).fetchone()
        categories = dict(self.connection.execute(
            "SELECT category, COUNT(*) FROM videos WHERE completed_at IS NULL GROUP BY category"
        ).fetchall())
        return {
            "total": row["total"],
            "pending": row["pending"] or 0,
            "completed": row["completed"] or 0,
            "pending_minutes": round(row["pending_seconds"] / 60, 1),
            "pending_by_category": categories,
        }

    @staticmethod
    def _video(row: sqlite3.Row) -> Video:
        return Video(
            video_id=row["video_id"],
            title=row["title"],
            channel=row["channel"],
            duration_seconds=row["duration_seconds"],
            added_at=datetime.fromisoformat(row["added_at"]),
            category=row["category"],
            priority=row["priority"],
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"] else None
            ),
        )
