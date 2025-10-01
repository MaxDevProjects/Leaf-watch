"""Domain services for ingestion and notifications."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Sequence

import feedparser
import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .config import Settings, get_settings
from .database import SessionFactory
from .models import Entry, Feed


@dataclass(slots=True)
class TopicRule:
    name: str
    keywords: Sequence[str]
    threshold: float = 1.0
    weight: float = 1.0

    def evaluate(self, text: str) -> float:
        """Return score for the given text."""
        text_lower = text.lower()
        score = 0.0
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                score += self.weight
        return score


@dataclass(slots=True)
class FeedConfig:
    name: str
    url: str
    topics: Sequence[str]


@dataclass(slots=True)
class NotificationItem:
    title: str
    link: str
    topics: List[str]
    summary: str | None
    score: float
    published_at: datetime
    feed: str


class TopicMatcher:
    def __init__(self, rules: Sequence[TopicRule]):
        self.rules = list(rules)

    def match(self, text: str) -> tuple[List[str], float]:
        matched: List[str] = []
        total_score = 0.0
        for rule in self.rules:
            score = rule.evaluate(text)
            if score >= rule.threshold:
                matched.append(rule.name)
                total_score += score
        return matched, total_score


def load_topics(path: str | None = None) -> Sequence[TopicRule]:
    settings = get_settings()
    topics_path = path or settings.topics_file
    if not topics_path.exists():
        raise FileNotFoundError(f"Topics configuration not found at {topics_path}")
    config = yaml.safe_load(topics_path.read_text())
    rules: List[TopicRule] = []
    for topic in config.get("topics", []):
        rules.append(
            TopicRule(
                name=topic["name"],
                keywords=topic.get("keywords", []),
                threshold=float(topic.get("threshold", 1.0)),
                weight=float(topic.get("weight", 1.0)),
            )
        )
    return rules


def load_feeds(path: str | None = None) -> Sequence[FeedConfig]:
    settings = get_settings()
    feeds_path = path or settings.feeds_file
    if not feeds_path.exists():
        raise FileNotFoundError(f"Feed configuration not found at {feeds_path}")
    config = yaml.safe_load(feeds_path.read_text())
    feeds: List[FeedConfig] = []
    for feed in config.get("feeds", []):
        feeds.append(FeedConfig(name=feed["name"], url=feed["url"], topics=feed.get("topics", [])))
    return feeds


class IngestionService:
    def __init__(self, settings: Settings | None = None, http_client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self.http_client = http_client or httpx.AsyncClient(timeout=20.0)
        self.topic_matcher = TopicMatcher(load_topics())

    async def close(self) -> None:
        await self.http_client.aclose()

    async def ingest_all(self) -> tuple[int, List[NotificationItem]]:
        feeds = load_feeds()
        tasks = [self._ingest_feed(feed_config) for feed_config in feeds]
        results = await asyncio.gather(*tasks)
        ingested = sum(result[0] for result in results)
        notifications: List[NotificationItem] = [item for result in results for item in result[1]]
        return ingested, notifications

    async def _ingest_feed(self, feed_config: FeedConfig) -> tuple[int, List[NotificationItem]]:
        async with SessionFactory() as session:
            feed = await self._get_or_create_feed(session, feed_config)
            response = await self.http_client.get(feed_config.url)
            response.raise_for_status()
            parsed = feedparser.parse(response.text)
            new_entries = 0
            notifications: List[NotificationItem] = []
            for entry in parsed.entries:
                title = entry.get("title", "Sans titre")
                summary = entry.get("summary")
                link = entry.get("link")
                published_parsed = entry.get("published_parsed")
                published_at = datetime.utcnow()
                if published_parsed:
                    published_at = datetime(*published_parsed[:6])
                text = " ".join(filter(None, [title, summary or "", link or ""]))
                matched_topics, score = self.topic_matcher.match(text)
                if not matched_topics:
                    continue
                db_entry = Entry(
                    feed_id=feed.id,
                    title=title,
                    summary=summary,
                    link=link,
                    published_at=published_at,
                    topics=",".join(matched_topics),
                    score=score,
                )
                session.add(db_entry)
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    continue
                await session.refresh(db_entry)
                new_entries += 1
                notifications.append(
                    NotificationItem(
                        title=title,
                        link=link,
                        topics=matched_topics,
                        summary=summary,
                        score=score,
                        published_at=published_at,
                        feed=feed.name,
                    )
                )
            return new_entries, notifications

    async def _get_or_create_feed(self, session, config: FeedConfig) -> Feed:
        result = await session.execute(select(Feed).where(Feed.url == config.url))
        feed = result.scalar_one_or_none()
        if feed:
            return feed
        feed = Feed(name=config.name, url=config.url)
        session.add(feed)
        await session.commit()
        await session.refresh(feed)
        return feed


class TelegramNotifier:
    def __init__(self, settings: Settings | None = None, http_client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self.http_client = http_client or httpx.AsyncClient(timeout=20.0)

    async def notify(self, items: Iterable[NotificationItem]) -> int:
        items = list(items)
        if not items or not self.settings.telegram_bot_token or not self.settings.telegram_chat_ids:
            return 0
        message = self._format_message(items)
        delivered = 0
        for chat_id in self.settings.telegram_chat_ids:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": True,
            }
            url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
            try:
                response = await self.http_client.post(url, json=payload)
                response.raise_for_status()
                delivered += 1
            except httpx.HTTPError:
                continue
        return delivered

    def _format_message(self, items: Sequence[NotificationItem]) -> str:
        lines = ["🌿 WebWatcher – nouvelles alertes"]
        for item in items:
            topics = ", ".join(item.topics)
            lines.append(f"• [{item.title}]({item.link}) — {topics} (score {item.score:.1f})")
        return "\n".join(lines)

    async def close(self) -> None:
        await self.http_client.aclose()


class EmailNotifier:
    def __init__(self, settings: Settings | None = None, http_client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self.http_client = http_client or httpx.AsyncClient(timeout=20.0)

    async def send_digest(self, items: Iterable[NotificationItem]) -> bool:
        items = list(items)
        if not items or not self.settings.brevo_api_key or not self.settings.brevo_recipients or not self.settings.brevo_sender:
            return False
        content_lines = ["<h1>🌿 WebWatcher – Digest</h1>"]
        for item in items:
            topics = ", ".join(item.topics)
            content_lines.append(
                f"<p><a href=\"{item.link}\">{item.title}</a><br/><small>{topics} · score {item.score:.1f}</small></p>"
            )
        payload = {
            "sender": {"email": self.settings.brevo_sender},
            "to": [{"email": email} for email in self.settings.brevo_recipients],
            "subject": "WebWatcher – Digest",
            "htmlContent": "".join(content_lines),
        }
        headers = {"api-key": self.settings.brevo_api_key}
        try:
            response = await self.http_client.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers)
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self.http_client.aclose()


async def run_ingestion() -> tuple[int, int]:
    settings = get_settings()
    ingestion = IngestionService(settings=settings)
    telegram = TelegramNotifier(settings=settings)
    try:
        ingested, items = await ingestion.ingest_all()
        notified = await telegram.notify(items)
        return ingested, notified
    finally:
        await ingestion.close()
        await telegram.close()
