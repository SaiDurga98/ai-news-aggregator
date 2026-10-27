from __future__ import annotations

from pathlib import Path

from app.converters.markdown import ArticleMarkdownConverter

_converter = ArticleMarkdownConverter()


def article_url_to_markdown(url: str) -> str:
    return _converter.url_to_markdown(url)


def article_url_to_markdown_file(url: str, output_path: str | Path) -> Path:
    return _converter.url_to_markdown_file(url, output_path)
