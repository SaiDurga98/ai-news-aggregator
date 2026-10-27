from __future__ import annotations

from datetime import datetime, timedelta, timezone

import feedparser
from pydantic import BaseModel

# Anthropic does not publish an official RSS feed (e.g. /news/rss.xml returns 404).
# This mirror is generated from https://www.anthropic.com/news and is easy to swap later.
ANTHROPIC_NEWS_RSS_URL = (
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml"
)
ANTHROPIC_NEWS_PAGE = "https://www.anthropic.com/news"


class AnthropicArticle(BaseModel):
    model_config = {"frozen": True}

    title: str
    description: str
    url: str
    guid: str
    published_at: datetime
    category: str | None = None


class AnthropicScraper:
    def __init__(self, rss_url: str = ANTHROPIC_NEWS_RSS_URL) -> None:
        self.rss_url = rss_url

    def get_articles(self, hours: int = 24) -> list[AnthropicArticle]:
        feed = feedparser.parse(self.rss_url)
        if not feed.entries:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        articles: list[AnthropicArticle] = []

        for entry in feed.entries:
            published_parsed = getattr(entry, "published_parsed", None)
            if not published_parsed:
                continue

            published_at = datetime(*published_parsed[:6], tzinfo=timezone.utc)
            if published_at < cutoff_time:
                continue

            tags = entry.get("tags")
            category = tags[0].get("term") if tags else None

            articles.append(
                AnthropicArticle(
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    url=entry.get("link", ""),
                    guid=entry.get("id", entry.get("link", "")),
                    published_at=published_at,
                    category=category,
                )
            )

        return articles
