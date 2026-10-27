from __future__ import annotations

from datetime import datetime, timedelta, timezone

import feedparser
from pydantic import BaseModel


class OpenAIArticle(BaseModel):
    model_config = {"frozen": True}

    title: str
    description: str
    url: str
    guid: str
    published_at: datetime
    category: str | None = None


class OpenAIScraper:
    def __init__(self) -> None:
        self.rss_url = "https://openai.com/news/rss.xml"

    def get_articles(self, hours: int = 24) -> list[OpenAIArticle]:
        feed = feedparser.parse(self.rss_url)
        if not feed.entries:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        articles: list[OpenAIArticle] = []

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
                OpenAIArticle(
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    url=entry.get("link", ""),
                    guid=entry.get("id", entry.get("link", "")),
                    published_at=published_at,
                    category=category,
                )
            )

        return articles
