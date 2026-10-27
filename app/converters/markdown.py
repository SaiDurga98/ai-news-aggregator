from __future__ import annotations

from pathlib import Path

from docling.document_converter import DocumentConverter


class ArticleMarkdownConverter:
    """Convert a web page or document URL to Markdown using Docling."""

    def __init__(self) -> None:
        self._converter = DocumentConverter()

    def url_to_markdown(self, url: str) -> str:
        result = self._converter.convert(url)
        return result.document.export_to_markdown()

    def url_to_markdown_file(self, url: str, output_path: str | Path) -> Path:
        markdown = self.url_to_markdown(url)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        return path
