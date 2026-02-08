"""Contracts for external integrations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Protocol


@dataclass(frozen=True)
class IntegrationAccount:
    integration_id: str
    external_id: str
    display_name: str
    metadata: Mapping[str, object] | None = None


class IntegrationConnector(Protocol):
    """Connects to an external system and validates credentials."""

    def connect(self, credentials: Mapping[str, object]) -> IntegrationAccount:
        """Validate credentials and return the integration account."""

    def disconnect(self, integration_id: str) -> None:
        """Revoke or deactivate the connection."""


@dataclass(frozen=True)
class SyncResult:
    integration_id: str
    started_at: datetime
    finished_at: datetime | None
    summary: Mapping[str, object]


class SyncService(Protocol):
    """Synchronizes data with an external system."""

    def sync(self, integration_id: str) -> SyncResult:
        """Run a full sync and return a summary result."""


@dataclass(frozen=True)
class WebhookEvent:
    integration_id: str
    event_type: str
    received_at: datetime
    payload: Mapping[str, object]


class WebhookHandler(Protocol):
    """Processes inbound webhook events."""

    def handle(self, event: WebhookEvent) -> Iterable[Mapping[str, object]]:
        """Handle the webhook and return any follow-up actions."""
