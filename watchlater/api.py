"""FastAPI application for the Watch Later Intelligence dashboard."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .domain import Video
from .inbox import recommend
from .store import VideoStore

PACKAGE_ROOT = Path(__file__).parent
STATIC_ROOT = PACKAGE_ROOT / "static"


class VideoInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    video_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=300)
    channel: str = Field(min_length=1, max_length=200)
    duration_seconds: int = Field(gt=0, le=86_400)
    added_at: datetime
    category: str = Field(default="uncategorized", min_length=1, max_length=80)
    priority: int = Field(default=3, ge=1, le=5)

    def to_domain(self) -> Video:
        return Video(**self.model_dump())


def database_path() -> Path:
    return Path(os.environ.get("WATCHLATER_DATABASE", ".watchlater/inbox.db"))


def get_store():
    with VideoStore(database_path(), initialize=False) as store:
        yield store


def create_app() -> FastAPI:
    with VideoStore(database_path()):
        pass
    app = FastAPI(
        title="Watch Later Intelligence",
        version="0.3.0",
        description="An explainable learning-queue API.",
    )

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(STATIC_ROOT / "index.html")

    @app.get("/styles.css", include_in_schema=False)
    def styles():
        return FileResponse(STATIC_ROOT / "styles.css", media_type="text/css")

    @app.get("/app.js", include_in_schema=False)
    def script():
        return FileResponse(
            STATIC_ROOT / "app.js", media_type="application/javascript"
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/stats")
    def stats(store: VideoStore = Depends(get_store)) -> dict[str, object]:
        return store.stats()

    @app.get("/api/recommendations")
    def recommendations(
        minutes: int = Query(default=25, ge=1, le=480),
        limit: int = Query(default=6, ge=1, le=50),
        store: VideoStore = Depends(get_store),
    ) -> list[dict[str, object]]:
        return [
            {
                "video_id": item.video.video_id,
                "title": item.video.title,
                "channel": item.video.channel,
                "duration_minutes": round(item.video.duration_seconds / 60, 1),
                "category": item.video.category,
                "priority": item.video.priority,
                "score": item.score,
                "reasons": item.reasons,
                "youtube_url": f"https://www.youtube.com/watch?v={item.video.video_id}",
            }
            for item in recommend(
                store, available_minutes=minutes, limit=limit
            )
        ]

    @app.post("/api/videos", status_code=201)
    def add_video(
        payload: VideoInput, store: VideoStore = Depends(get_store)
    ) -> dict[str, object]:
        store.upsert([payload.to_domain()])
        return {"video_id": payload.video_id, "created": True}

    @app.post("/api/videos/{video_id}/complete")
    def complete(
        video_id: str, store: VideoStore = Depends(get_store)
    ) -> dict[str, object]:
        if not store.complete(video_id):
            raise HTTPException(status_code=404, detail="Pending video not found")
        return {"video_id": video_id, "completed": True}

    return app


app = create_app()
