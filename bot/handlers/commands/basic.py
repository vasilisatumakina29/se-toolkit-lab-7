"""Basic plain-function handlers."""

from __future__ import annotations

from handlers.common import HandlerContext


async def handle_start(context: HandlerContext) -> str:
    del context
    return "LMS bot scaffold is running.\nUse /help to see available commands."


async def handle_help(context: HandlerContext) -> str:
    del context
    return (
        "Available commands:\n"
        "/start - show welcome message\n"
        "/help - list commands\n"
        "/health - check backend connectivity\n"
        "/labs - list labs\n"
        "/scores <lab-id> - show score buckets"
    )
