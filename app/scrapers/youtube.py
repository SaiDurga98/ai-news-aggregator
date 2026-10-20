from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi

ATOM_NS = "http://www.w3.org/2005/Atom"
MEDIA_NS = "http://search.yahoo.com/mrss/"
YT_NS = "http://www.youtube.com/xml/schemas/2015"
CHANNEL_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
CHANNEL_VIDEOS_URL = "https://www.youtube.com/channel/{channel_id}/videos"
OEMBED_URL = "https://www.youtube.com/oembed"
WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
YT_INITIAL_DATA_RE = re.compile(r"var ytInitialData = ({.*?});\s*</script>", re.DOTALL)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/atom+xml, application/json, text/html;q=0.9, */*;q=0.8",
}


class YouTubeScraperError(RuntimeError):
    pass


class YouTubeVideo(BaseModel):
    model_config = {"frozen": True}

    video_id: str
    title: str
    url: str
    channel_id: str | None = None
    channel_title: str | None = None
    published_at: datetime | None = None
    description: str | None = None
    thumbnail_url: str | None = None


class YouTubeTranscript(BaseModel):
    model_config = {"frozen": True}

    video_id: str
    language_code: str
    is_generated: bool
    text: str


def channel_feed_url(channel_id: str) -> str:
    return CHANNEL_FEED_URL.format(channel_id=channel_id)


def video_watch_url(video_id: str) -> str:
    return WATCH_URL.format(video_id=video_id)


def fetch_channel_videos(channel_id: str) -> list[YouTubeVideo]:
    rss_error: Exception | None = None
    for attempt in range(2):
        try:
            xml_text = _get_text(channel_feed_url(channel_id))
            videos = parse_channel_feed(xml_text, fallback_channel_id=channel_id)
            if videos:
                return videos
        except YouTubeScraperError as exc:
            rss_error = exc
            if attempt == 0:
                time.sleep(0.5)

    try:
        html = _get_text(CHANNEL_VIDEOS_URL.format(channel_id=channel_id))
        videos = parse_channel_page(html, channel_id=channel_id)
        if videos:
            return videos
    except YouTubeScraperError as page_error:
        raise YouTubeScraperError(
            f"Could not load videos for channel {channel_id}"
        ) from page_error

    if rss_error:
        raise YouTubeScraperError(
            f"Could not load videos for channel {channel_id}"
        ) from rss_error
    raise YouTubeScraperError(f"No videos found for channel {channel_id}")


def fetch_video(video_id: str) -> YouTubeVideo:
    params = {"url": video_watch_url(video_id), "format": "json"}
    payload = _get_json(OEMBED_URL, params=params)
    return YouTubeVideo(
        video_id=video_id,
        title=payload.get("title") or video_id,
        url=video_watch_url(video_id),
        channel_id=None,
        channel_title=payload.get("author_name"),
        published_at=None,
        description=None,
        thumbnail_url=payload.get("thumbnail_url"),
    )


def fetch_transcript(
    video_id: str,
    languages: tuple[str, ...] = ("en",),
) -> YouTubeTranscript:
    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=list(languages))
    except Exception:
        try:
            fetched = _fetch_any_transcript(api, video_id, languages)
        except Exception as exc:
            raise YouTubeScraperError(
                f"Could not fetch a transcript for video {video_id}"
            ) from exc

    text = " ".join(
        snippet.text.replace("\n", " ").strip() for snippet in fetched
    )
    return YouTubeTranscript(
        video_id=video_id,
        language_code=fetched.language_code,
        is_generated=fetched.is_generated,
        text=" ".join(text.split()),
    )


def parse_channel_feed(xml_text: str, fallback_channel_id: str | None = None) -> list[YouTubeVideo]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise YouTubeScraperError("YouTube channel feed was not valid XML") from exc

    feed_channel_id = _child_text(root, YT_NS, "channelId") or fallback_channel_id
    feed_title = _child_text(root, ATOM_NS, "title")
    videos: list[YouTubeVideo] = []

    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        video_id = _child_text(entry, YT_NS, "videoId")
        if not video_id:
            continue
        media_group = entry.find(f"{{{MEDIA_NS}}}group")
        thumbnail = None
        description = None
        if media_group is not None:
            description = _child_text(media_group, MEDIA_NS, "description")
            thumb = media_group.find(f"{{{MEDIA_NS}}}thumbnail")
            if thumb is not None:
                thumbnail = thumb.attrib.get("url")

        videos.append(
            YouTubeVideo(
                video_id=video_id,
                title=_child_text(entry, ATOM_NS, "title") or video_id,
                url=_entry_link(entry) or video_watch_url(video_id),
                channel_id=_child_text(entry, YT_NS, "channelId") or feed_channel_id,
                channel_title=feed_title,
                published_at=_parse_datetime(_child_text(entry, ATOM_NS, "published")),
                description=description,
                thumbnail_url=thumbnail,
            )
        )
    return videos


def parse_channel_page(html: str, channel_id: str) -> list[YouTubeVideo]:
    match = YT_INITIAL_DATA_RE.search(html)
    if not match:
        raise YouTubeScraperError("Could not parse YouTube channel page")

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise YouTubeScraperError("YouTube channel page JSON was invalid") from exc

    channel_title = _nested_text(data, ("metadata", "channelMetadataRenderer", "title"))
    videos: list[YouTubeVideo] = []
    seen: set[str] = set()

    for lockup in _walk_lockups(data):
        if lockup.get("contentType") != "LOCKUP_CONTENT_TYPE_VIDEO":
            continue
        video_id = lockup.get("contentId")
        if not isinstance(video_id, str) or video_id in seen:
            continue
        seen.add(video_id)
        videos.append(
            YouTubeVideo(
                video_id=video_id,
                title=_lockup_title(lockup) or video_id,
                url=video_watch_url(video_id),
                channel_id=channel_id,
                channel_title=channel_title,
                published_at=None,
                description=None,
                thumbnail_url=_lockup_thumbnail(lockup),
            )
        )
    return videos


def _walk_lockups(obj: object):
    if isinstance(obj, dict):
        lockup = obj.get("lockupViewModel")
        if isinstance(lockup, dict):
            yield lockup
        for value in obj.values():
            yield from _walk_lockups(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_lockups(value)


def _lockup_title(lockup: dict) -> str | None:
    return _nested_text(
        lockup,
        ("metadata", "lockupMetadataViewModel", "title", "content"),
    )


def _lockup_thumbnail(lockup: dict) -> str | None:
    sources = _nested_get(
        lockup,
        ("contentImage", "thumbnailViewModel", "image", "sources"),
    )
    if isinstance(sources, list) and sources:
        first = sources[0]
        if isinstance(first, dict) and isinstance(first.get("url"), str):
            return first["url"]
    return None


def _nested_get(obj: object, path: tuple[str, ...]) -> object | None:
    current: object = obj
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _nested_text(obj: object, path: tuple[str, ...]) -> str | None:
    value = _nested_get(obj, path)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _fetch_any_transcript(
    api: YouTubeTranscriptApi,
    video_id: str,
    languages: tuple[str, ...],
):
    transcript_list = api.list(video_id)
    try:
        return transcript_list.find_generated_transcript(list(languages)).fetch()
    except Exception:
        first = next(iter(transcript_list))
        return first.fetch()


def _get_text(url: str) -> str:
    try:
        with httpx.Client(headers=REQUEST_HEADERS, timeout=20.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPError as exc:
        raise YouTubeScraperError(f"Failed to fetch {url}") from exc


def _get_json(url: str, params: dict[str, str] | None = None) -> dict:
    try:
        with httpx.Client(headers=REQUEST_HEADERS, timeout=20.0, follow_redirects=True) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise YouTubeScraperError(f"Failed to fetch {url}") from exc


def _child_text(element: ElementTree.Element, namespace: str, tag: str) -> str | None:
    child = element.find(f"{{{namespace}}}{tag}")
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _entry_link(entry: ElementTree.Element) -> str | None:
    link = entry.find(f"{{{ATOM_NS}}}link")
    if link is None:
        return None
    return link.attrib.get("href")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
