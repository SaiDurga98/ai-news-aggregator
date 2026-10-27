from __future__ import annotations

from app.scrapers.anthropic_news import AnthropicArticle, AnthropicScraper

_scraper = AnthropicScraper()


def get_anthropic_articles(hours: int = 24) -> list[AnthropicArticle]:
    return _scraper.get_articles(hours=hours)
