from __future__ import annotations

from importlib import reload
from pathlib import Path

import pytest
from sqlalchemy import select

from apps.backend.app import config as config_module


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    project_root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("WEBWATCHER_DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("WEBWATCHER_TOPICS_FILE", str(project_root / "config" / "topics.yaml"))
    monkeypatch.setenv("WEBWATCHER_FEEDS_FILE", str(project_root / "config" / "feeds.yaml"))

    reload(config_module)
    from apps.backend.app import database as database_module
    from apps.backend.app import services as services_module

    reload(database_module)
    reload(services_module)
    yield


@pytest.mark.asyncio
async def test_topic_matcher_scores_text():
    from apps.backend.app import services

    matcher = services.TopicMatcher(
        [
            services.TopicRule(name="tech", keywords=["ai", "cloud"], threshold=1, weight=1),
            services.TopicRule(name="design", keywords=["design"], threshold=1, weight=1),
        ]
    )

    topics, score = matcher.match("AI design trends for 2024")
    assert "tech" in topics
    assert "design" in topics
    assert score >= 2


class DummyResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


class DummyClient:
    def __init__(self, text: str):
        self._response = DummyResponse(text)

    async def get(self, url: str):  # noqa: D401
        return self._response

    async def aclose(self) -> None:  # noqa: D401
        return None


@pytest.mark.asyncio
async def test_ingestion_creates_entries(monkeypatch):
    from apps.backend.app import database, services
    from apps.backend.app.models import Entry

    sample_feed = """
    <rss><channel>
      <item>
        <title>AI breakthrough for climate impact</title>
        <link>https://example.com/ai</link>
        <description>Designing low-carbon AI systems.</description>
        <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
      </item>
      <item>
        <title>Random sports news</title>
        <link>https://example.com/sport</link>
        <description>Score update.</description>
      </item>
    </channel></rss>
    """

    dummy_client = DummyClient(sample_feed)
    monkeypatch.setattr(services, "load_feeds", lambda path=None: [services.FeedConfig(name="Dummy", url="http://dummy", topics=["tech"])])
    ingestion = services.IngestionService(http_client=dummy_client)

    ingested, items = await ingestion.ingest_all()

    assert ingested == 1
    assert len(items) == 1
    assert items[0].link == "https://example.com/ai"
    assert "tech" in items[0].topics

    async with database.SessionFactory() as session:
        result = await session.execute(select(Entry))
        stored = result.scalars().all()
        assert len(stored) == 1
        assert stored[0].link == "https://example.com/ai"

    await ingestion.close()
