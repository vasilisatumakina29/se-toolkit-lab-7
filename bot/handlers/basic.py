"""Basic command handlers with no Telegram dependency."""

from __future__ import annotations

from handlers.common import HandlerContext


async def handle_start(context: HandlerContext) -> str:
    """Return the welcome text."""
    return (
        "LMS bot scaffold is running.\n"
        "Use /help to see available commands."
    )


async def handle_help(context: HandlerContext) -> str:
    """Return supported commands."""
    return (
        "Available commands:\n"
        "/start - show welcome message\n"
        "/help - list commands\n"
        "/health - check backend connectivity\n"
        "/labs - list labs\n"
        "/scores <lab-id> - show score buckets"
    )
