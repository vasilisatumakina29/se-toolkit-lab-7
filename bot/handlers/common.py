"""Shared types for bot handlers."""

from __future__ import annotations

from dataclasses import dataclass

from services import ServiceContainer


@dataclass(slots=True)
class HandlerContext:
    """Values shared across command handlers."""

    services: ServiceContainer
