"""Handlers that talk to the LMS service layer."""

from __future__ import annotations

from handlers.common import HandlerContext


async def handle_health(context: HandlerContext) -> str:
    """Return backend health text."""
    return await context.services.lms.get_health()


async def handle_labs(context: HandlerContext) -> str:
    """Return available labs."""
    return await context.services.lms.list_labs()


async def handle_scores(context: HandlerContext, lab: str | None) -> str:
    """Return score information for a lab."""
    return await context.services.lms.get_scores(lab or "")
