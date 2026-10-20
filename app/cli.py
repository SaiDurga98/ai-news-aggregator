import argparse
import json

from pydantic import BaseModel

from app.database import SessionLocal, init_db
from app.seed import seed_sources
from app.services.youtube import get_channel_videos, get_transcript, get_video


def cmd_init_db() -> None:
    init_db()
    with SessionLocal() as session:
        created = seed_sources(session)
    print(f"Database tables are ready. Seeded {created} new source(s).")


def cmd_youtube_channel(args: argparse.Namespace) -> None:
    videos = get_channel_videos(args.channel_id)
    print(_to_json(videos))


def cmd_youtube_video(args: argparse.Namespace) -> None:
    video = get_video(args.video_id)
    print(_to_json(video))


def cmd_youtube_transcript(args: argparse.Namespace) -> None:
    transcript = get_transcript(args.video_id)
    print(transcript.text)


def _to_json(value: object) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
        value = [item.model_dump(mode="json") for item in value]
    return json.dumps(value, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI news aggregator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Create tables and seed sources")
    init_parser.set_defaults(func=lambda _: cmd_init_db())

    youtube_parser = subparsers.add_parser("youtube", help="Fetch YouTube channel or video data")
    youtube_sub = youtube_parser.add_subparsers(dest="youtube_command", required=True)

    channel_parser = youtube_sub.add_parser("channel", help="List latest videos from a channel RSS feed")
    channel_parser.add_argument("channel_id", help="Channel ID (UC...) or /channel/UC... URL")
    channel_parser.set_defaults(func=cmd_youtube_channel)

    video_parser = youtube_sub.add_parser("video", help="Fetch metadata for a video ID")
    video_parser.add_argument("video_id", help="Video ID or YouTube URL")
    video_parser.set_defaults(func=cmd_youtube_video)

    transcript_parser = youtube_sub.add_parser("transcript", help="Fetch a video transcript")
    transcript_parser.add_argument("video_id", help="Video ID or YouTube URL")
    transcript_parser.set_defaults(func=cmd_youtube_transcript)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
