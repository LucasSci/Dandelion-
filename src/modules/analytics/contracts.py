"""Contracts for analytics capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class AnalyticsEvent:
    name: str
    occurred_at: datetime
    payload: Mapping[str, object]
    actor_id: str | None = None
    source: str | None = None


class EventRecorder(Protocol):
    """Records analytics events for later aggregation."""

    def record(self, event: AnalyticsEvent) -> None:
        """Persist an event for analytics processing."""


@dataclass(frozen=True)
class AnalyticsQuery:
    metric: str
    start_at: datetime
    end_at: datetime
    filters: Mapping[str, object] | None = None
    group_by: Sequence[str] | None = None


class AnalyticsQueryService(Protocol):
    """Executes analytics queries and returns metric data."""

    def run(self, query: AnalyticsQuery) -> Iterable[Mapping[str, object]]:
        """Return rows with aggregated metrics."""


@dataclass(frozen=True)
class AnalyticsReport:
    title: str
    generated_at: datetime
    sections: Sequence[Mapping[str, object]]


class ReportBuilder(Protocol):
    """Builds human-readable reports from analytics data."""

    def build(self, title: str, queries: Sequence[AnalyticsQuery]) -> AnalyticsReport:
        """Run queries and assemble a report."""
