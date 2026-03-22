"""Router from plain text input to handler functions."""

from __future__ import annotations

from handlers.basic import handle_help, handle_start
from handlers.common import HandlerContext
from handlers.lms import handle_health, handle_labs, handle_scores
from services import ServiceContainer


async def handle_text(text: str, services: ServiceContainer) -> str:
    """Handle a command or free-form text and return a text response."""
    normalized = text.strip()
    context = HandlerContext(services=services)

    if not normalized:
        return "Please enter a command. Try /help."

    command, _, rest = normalized.partition(" ")
    argument = rest.strip() or None

    match command.lower():
        case "/start":
            return await handle_start(context)
        case "/help":
            return await handle_help(context)
        case "/health":
            return await handle_health(context)
        case "/labs":
            return await handle_labs(context)
        case "/scores":
            return await handle_scores(context, argument)
        case _:
            return await services.llm.explain_unknown_request(normalized)
