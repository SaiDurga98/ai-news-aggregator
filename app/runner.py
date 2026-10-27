from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.monitor_config import MonitorConfig, load_monitor_config
from app.scrapers.anthropic_news import AnthropicArticle
from app.scrapers.openai_news import OpenAIArticle
from app.scrapers.youtube import YouTubeVideo
from app.services.anthropic_news import get_anthropic_articles
from app.services.openai_news import get_openai_articles
from app.services.youtube import get_channel_videos


class CollectionResult(BaseModel):
    hours: int
    openai_articles: list[OpenAIArticle] = Field(default_factory=list)
    anthropic_articles: list[AnthropicArticle] = Field(default_factory=list)
    youtube_videos: list[YouTubeVideo] = Field(default_factory=list)


def run_collection(
    hours: int = 24,
    config_path: Path | None = None,
) -> CollectionResult:
    """Fetch OpenAI + Anthropic news and YouTube videos from configured channels."""
    config = load_monitor_config(config_path)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    youtube_videos: list[YouTubeVideo] = []
    for channel_id in config.youtube_channels:
        for video in get_channel_videos(channel_id):
            if video.published_at is not None and video.published_at >= cutoff:
                youtube_videos.append(video)

    return CollectionResult(
        hours=hours,
        openai_articles=get_openai_articles(hours=hours),
        anthropic_articles=get_anthropic_articles(hours=hours),
        youtube_videos=youtube_videos,
    )
