"""Pydantic schemas used by the API."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, HttpUrl


class EntryOut(BaseModel):
    id: int
    feed: str
    title: str
    summary: str | None
    link: HttpUrl
    published_at: datetime
    topics: List[str]
    score: float


class HealthResponse(BaseModel):
    status: str = "ok"


class HookResponse(BaseModel):
    ingested: int
    notified: int
