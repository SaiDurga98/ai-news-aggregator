from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel

from app.scrapers.youtube import (
    YouTubeScraperError,
    YouTubeTranscript,
    YouTubeVideo,
    fetch_channel_videos,
    fetch_transcript,
    fetch_video,
)

CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
VIDEO_ID_RE = re.compile(r"^[\w-]{11}$")


class YouTubeVideoWithTranscript(BaseModel):
    model_config = {"frozen": True}

    video: YouTubeVideo
    transcript: YouTubeTranscript | None = None


def get_channel_videos(channel_id_or_url: str) -> list[YouTubeVideo]:
    channel_id = extract_channel_id(channel_id_or_url)
    videos = fetch_channel_videos(channel_id)
    if not videos:
        raise YouTubeScraperError(f"No videos found for channel {channel_id}")
    return videos


def get_video(video_id_or_url: str) -> YouTubeVideo:
    video_id = extract_video_id(video_id_or_url)
    return fetch_video(video_id)


def get_transcript(
    video_id_or_url: str,
    languages: tuple[str, ...] = ("en",),
) -> YouTubeTranscript:
    video_id = extract_video_id(video_id_or_url)
    return fetch_transcript(video_id, languages=languages)


def get_video_with_transcript(
    video_id_or_url: str,
    languages: tuple[str, ...] = ("en",),
    require_transcript: bool = False,
) -> YouTubeVideoWithTranscript:
    video = get_video(video_id_or_url)
    try:
        transcript = get_transcript(video.video_id, languages=languages)
    except YouTubeScraperError:
        if require_transcript:
            raise
        transcript = None
    return YouTubeVideoWithTranscript(video=video, transcript=transcript)


def extract_channel_id(value: str) -> str:
    text = value.strip()
    if CHANNEL_ID_RE.match(text):
        return text

    parsed = urlparse(text)
    path_parts = [part for part in parsed.path.split("/") if part]
    if "channel" in path_parts:
        index = path_parts.index("channel")
        if index + 1 < len(path_parts) and CHANNEL_ID_RE.match(path_parts[index + 1]):
            return path_parts[index + 1]

    raise YouTubeScraperError(
        "Pass a channel ID (starts with UC) or a youtube.com/channel/UC... URL"
    )


def extract_video_id(value: str) -> str:
    text = value.strip()
    if VIDEO_ID_RE.match(text):
        return text

    parsed = urlparse(text)
    host = (parsed.netloc or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if host.endswith("youtu.be") and path_parts:
        candidate = path_parts[0]
        if VIDEO_ID_RE.match(candidate):
            return candidate

    query_id = parse_qs(parsed.query).get("v", [None])[0]
    if query_id and VIDEO_ID_RE.match(query_id):
        return query_id

    if path_parts and path_parts[0] in {"embed", "shorts", "live"} and len(path_parts) > 1:
        candidate = path_parts[1]
        if VIDEO_ID_RE.match(candidate):
            return candidate

    raise YouTubeScraperError("Pass an 11-character video ID or a YouTube watch URL")
