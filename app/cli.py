import argparse
import json

from pydantic import BaseModel

from app.database import SessionLocal, init_db
from app.seed import seed_sources
from app.services.anthropic_news import get_anthropic_articles
from app.services.openai_news import get_openai_articles
from app.runner import run_collection
from app.services.markdown import article_url_to_markdown, article_url_to_markdown_file
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


def cmd_openai_articles(args: argparse.Namespace) -> None:
    articles = get_openai_articles(hours=args.hours)
    print(_to_json(articles))


def cmd_anthropic_articles(args: argparse.Namespace) -> None:
    articles = get_anthropic_articles(hours=args.hours)
    print(_to_json(articles))


def cmd_run(args: argparse.Namespace) -> None:
    result = run_collection(hours=args.hours)
    print(_to_json(result))


def cmd_article_markdown(args: argparse.Namespace) -> None:
    if args.output:
        path = article_url_to_markdown_file(args.url, args.output)
        print(path)
        return
    print(article_url_to_markdown(args.url))


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

    run_parser = subparsers.add_parser(
        "run",
        help="Collect OpenAI, Anthropic, and configured YouTube sources",
    )
    run_parser.add_argument(
        "--hours",
        type=int,
        default=24,
        metavar="N",
        help="How far back to look (default: 24)",
    )
    run_parser.set_defaults(func=cmd_run)

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

    openai_parser = subparsers.add_parser("openai", help="Fetch OpenAI news articles")
    openai_sub = openai_parser.add_subparsers(dest="openai_command", required=True)

    articles_parser = openai_sub.add_parser(
        "articles",
        help="List articles from the OpenAI news RSS feed within a time window",
    )
    articles_parser.add_argument(
        "--hours",
        type=int,
        default=24,
        metavar="N",
        help="Only include posts from the last N hours (default: 24)",
    )
    articles_parser.set_defaults(func=cmd_openai_articles)

    anthropic_parser = subparsers.add_parser("anthropic", help="Fetch Anthropic news articles")
    anthropic_sub = anthropic_parser.add_subparsers(dest="anthropic_command", required=True)

    anthropic_articles_parser = anthropic_sub.add_parser(
        "articles",
        help="List articles from the Anthropic news feed within a time window",
    )
    anthropic_articles_parser.add_argument(
        "--hours",
        type=int,
        default=24,
        metavar="N",
        help="Only include posts from the last N hours (default: 24)",
    )
    anthropic_articles_parser.set_defaults(func=cmd_anthropic_articles)

    markdown_parser = subparsers.add_parser(
        "markdown",
        help="Convert an article URL to Markdown (Docling)",
    )
    markdown_parser.add_argument("url", help="Article or document URL")
    markdown_parser.add_argument(
        "-o",
        "--output",
        help="Write Markdown to this file instead of printing to stdout",
    )
    markdown_parser.set_defaults(func=cmd_article_markdown)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
