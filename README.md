# Watch Later Intelligence

A local-first learning inbox that turns a YouTube backlog into a focused,
explainable queue—without sending users into the discovery feed.

## Features

- Ranks videos by priority, time fit, age, and topic diversity
- Explains every recommendation
- Plays selected videos in a privacy-enhanced embedded viewer
- Tracks completed videos and backlog statistics in SQLite
- Imports CSV or JSONL metadata idempotently
- Provides a responsive dashboard, FastAPI API, and CLI
- Keeps Selenium playback as an optional authenticated adapter

No Google credentials are collected or stored.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[test]"

watchlater import examples/videos.csv
uvicorn watchlater.api:app --reload
```

Open:

- Dashboard: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/docs`

The database defaults to `.watchlater/inbox.db`. Set `WATCHLATER_DATABASE` to
use another location.

## CLI

```bash
watchlater import examples/videos.csv
watchlater recommend --minutes 25 --limit 3
watchlater complete ml001
watchlater stats
```

Input records require `video_id`, `title`, `channel`, `duration_seconds`, and
`added_at`. Optional fields are `category` and `priority` (1–5).

## Ranking

```text
score = 0.35 priority
      + 0.30 fit-to-time-budget
      + 0.20 backlog age
      + 0.15 category diversity
```

This is a transparent baseline, not a claim of learned personalization.

## Test

```bash
pytest
```

## Architecture

- `watchlater/domain.py` — models and ranking policy
- `watchlater/store.py` — SQLite persistence and lifecycle events
- `watchlater/inbox.py` — import and recommendation services
- `watchlater/api.py` — FastAPI backend
- `watchlater/static/` — responsive focus-mode dashboard
- `watchlater/automation.py` — optional Selenium adapter

The embedded player avoids YouTube's home feed, although YouTube may still show
limited related content inside its own player.
