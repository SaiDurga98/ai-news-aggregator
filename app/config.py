import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    digest_recipient: str
    digest_system_prompt_path: str


def get_settings() -> Settings:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://news:news@localhost:5432/news",
    )
    return Settings(
        database_url=database_url,
        digest_recipient=os.getenv("DIGEST_RECIPIENT", ""),
        digest_system_prompt_path=os.getenv(
            "DIGEST_SYSTEM_PROMPT_PATH",
            "app/prompts/digest_system.md",
        ),
    )
