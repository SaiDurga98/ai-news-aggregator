# AI news aggregator

Python backend that collects AI news from YouTube channels and lab blogs, stores them in PostgreSQL, and (next) emails a short daily digest.

## How it will work

1. **Sources** live in the database. YouTube sources use a channel RSS URL (`https://www.youtube.com/feeds/videos.xml?channel_id=...`). Blog sources store a listing URL, preferably an RSS feed when the site has one.
2. **Ingest** (next) pulls new items into `articles` with a stable `external_id` so reruns are idempotent.
3. **Daily digest** (next) selects articles in a time window, summarizes them with an LLM using `app/prompts/digest_system.md` as the reader-specific system prompt, and stores snippet + original URL.
4. **Email** (next) sends that digest to `DIGEST_RECIPIENT`.
5. **Render** later: one Postgres instance, one cron/worker that runs ingest → digest → email every 24 hours.

## Starting point

This repo currently has the app layout, SQLAlchemy models, and a local Postgres container.

```text
app/
  agents/            # LLM digest agents (next)
  scrapers/          # YouTube RSS, oEmbed, transcripts
  services/          # public functions other code should call
  models.py
  database.py
  cli.py
  prompts/
docker/
```

YouTube (no API key):

```bash
uv run python main.py youtube channel UCsBjURrPoezykLs9EqgamOA
uv run python main.py youtube video dQw4w9WgXcQ
uv run python main.py youtube transcript dQw4w9WgXcQ
```

Call `app.services.youtube.get_channel_videos`, `get_video`, and `get_transcript` with a raw ID or a full YouTube URL. Channel listings try the public RSS feed first, then the channel videos page if RSS is down. Transcripts use `youtube-transcript-api`.

## Run locally

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
uv sync
uv run python main.py init-db
```

`init-db` creates tables and seeds OpenAI and Mistral blog sources. Add YouTube channels by inserting `Source` rows with `type=youtube` and the channel RSS URL (and `identifier` set to the channel id).
