from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Source, SourceType

INITIAL_SOURCES: list[dict] = [
    {
        "name": "OpenAI Blog",
        "type": SourceType.BLOG,
        "url": "https://openai.com/news/",
        "identifier": None,
    },
    {
        "name": "Mistral Blog",
        "type": SourceType.BLOG,
        "url": "https://mistral.ai/news",
        "identifier": None,
    },
]


def seed_sources(session: Session) -> int:
    created = 0
    for item in INITIAL_SOURCES:
        exists = session.scalar(
            select(Source).where(
                Source.type == item["type"],
                Source.url == item["url"],
            )
        )
        if exists:
            continue
        session.add(Source(**item))
        created += 1
    session.commit()
    return created
