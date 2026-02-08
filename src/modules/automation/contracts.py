"""Contracts for automation capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True)
class AutomationContext:
    triggered_at: datetime
    actor_id: str | None = None
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    parameters: Mapping[str, object]


class WorkflowRunner(Protocol):
    """Executes a workflow by name with a context payload."""

    def run(self, workflow_name: str, steps: Sequence[WorkflowStep], context: AutomationContext) -> None:
        """Run the workflow steps in sequence."""


class RuleEvaluator(Protocol):
    """Evaluates automation rules to decide if a workflow should run."""

    def should_run(self, rule_name: str, context: AutomationContext) -> bool:
        """Return True when the rule matches the context."""


@dataclass(frozen=True)
class ScheduledJob:
    name: str
    schedule: str
    workflow_name: str


class AutomationJobScheduler(Protocol):
    """Manages scheduled automation jobs."""

    def register(self, job: ScheduledJob) -> None:
        """Register or update a scheduled job."""

    def unregister(self, job_name: str) -> None:
        """Remove a scheduled job by name."""
