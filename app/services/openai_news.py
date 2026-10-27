from __future__ import annotations

from app.scrapers.openai_news import OpenAIArticle, OpenAIScraper

_scraper = OpenAIScraper()


def get_openai_articles(hours: int = 24) -> list[OpenAIArticle]:
    return _scraper.get_articles(hours=hours)
