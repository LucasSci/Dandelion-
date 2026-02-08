"""Contracts for administrative capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True)
class AdminUser:
    user_id: str
    email: str
    display_name: str
    is_active: bool


class UserAdminService(Protocol):
    """Manages user lifecycle and access in the admin domain."""

    def provision(self, email: str, display_name: str) -> AdminUser:
        """Create a user and return the admin representation."""

    def deactivate(self, user_id: str) -> AdminUser:
        """Deactivate an existing user."""


@dataclass(frozen=True)
class PermissionAssignment:
    user_id: str
    permissions: Sequence[str]
    granted_at: datetime


class PermissionService(Protocol):
    """Grants and audits permissions."""

    def grant(self, user_id: str, permissions: Sequence[str]) -> PermissionAssignment:
        """Grant permissions to a user."""

    def revoke(self, user_id: str, permissions: Sequence[str]) -> PermissionAssignment:
        """Revoke permissions from a user."""


class ConfigService(Protocol):
    """Stores and retrieves global configuration."""

    def get(self, key: str) -> Mapping[str, object] | None:
        """Fetch configuration by key."""

    def set(self, key: str, value: Mapping[str, object]) -> None:
        """Store configuration value for a key."""
