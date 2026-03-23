"""LMS-related plain-function handlers."""

from __future__ import annotations

from handlers.common import HandlerContext


async def handle_health(context: HandlerContext) -> str:
    return await context.services.lms.get_health()


async def handle_labs(context: HandlerContext) -> str:
    return await context.services.lms.list_labs()


async def handle_scores(context: HandlerContext, lab: str | None) -> str:
    return await context.services.lms.get_scores(lab or "")
