"""Command-line interface for the Watch Later knowledge inbox."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .automation import AutomationConfig, WatchLaterAutomation
from .inbox import load_videos, recommend
from .store import VideoStore


DEFAULT_DATABASE = Path(".watchlater/inbox.db")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"level": record.levelname, "event": record.getMessage()})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prioritize and play a local-first YouTube knowledge inbox"
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    commands = parser.add_subparsers(dest="command", required=True)

    import_parser = commands.add_parser("import", help="Import CSV or JSONL metadata")
    import_parser.add_argument("path", type=Path)

    recommend_parser = commands.add_parser(
        "recommend", help="Build an explainable viewing queue"
    )
    recommend_parser.add_argument("--minutes", type=int, required=True)
    recommend_parser.add_argument("--limit", type=int, default=5)

    complete_parser = commands.add_parser("complete", help="Mark a video completed")
    complete_parser.add_argument("video_id")

    commands.add_parser("stats", help="Show backlog and completion statistics")

    play_parser = commands.add_parser("play", help="Open YouTube Watch Later")
    play_parser.add_argument("--profile-directory", type=Path, required=True)
    play_parser.add_argument("--shuffle", action="store_true")
    play_parser.add_argument("--headless", action="store_true")
    play_parser.add_argument("--dry-run", action="store_true")
    play_parser.add_argument("--timeout", type=int, default=20)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "play":
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger = logging.getLogger("watchlater")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        state = WatchLaterAutomation(
            AutomationConfig(
                profile_directory=args.profile_directory,
                timeout_seconds=args.timeout,
                shuffle=args.shuffle,
                headless=args.headless,
                dry_run=args.dry_run,
            ),
            logger=logger,
        ).run()
        print(json.dumps({"state": state.value}))
        return

    with VideoStore(args.database) as store:
        if args.command == "import":
            print(json.dumps({"imported": store.upsert(load_videos(args.path))}))
        elif args.command == "recommend":
            if args.minutes <= 0 or args.limit <= 0:
                raise SystemExit("--minutes and --limit must be positive")
            output = [
                {
                    "video_id": item.video.video_id,
                    "title": item.video.title,
                    "channel": item.video.channel,
                    "duration_minutes": round(item.video.duration_seconds / 60, 1),
                    "category": item.video.category,
                    "score": item.score,
                    "reasons": item.reasons,
                }
                for item in recommend(
                    store, available_minutes=args.minutes, limit=args.limit
                )
            ]
            print(json.dumps(output, indent=2))
        elif args.command == "complete":
            changed = store.complete(args.video_id)
            print(json.dumps({"video_id": args.video_id, "completed": changed}))
        elif args.command == "stats":
            print(json.dumps(store.stats(), indent=2))


if __name__ == "__main__":
    main()
