"""Bot entry point for Telegram mode and offline CLI test mode."""


from __future__ import annotations

##import libraries
import argparse
import asyncio
import sys

##import aiogram packages
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import load_settings
from handlers import handle_text
from services import ServiceContainer


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="LMS bot entry point")
    parser.add_argument(
        "--test",
        metavar="TEXT",
        help='Run in offline mode, for example: --test "/start"',
    )
    return parser.parse_args()


async def run_test_mode(text: str) -> int:
    """Handle a request without connecting to Telegram."""
    settings = load_settings()
    services = ServiceContainer.from_settings(settings)
    response = await handle_text(text, services)
    print(response)
    return 0


async def run_telegram_mode() -> int:
    """Start Telegram polling."""
    settings = load_settings()
    services = ServiceContainer.from_settings(settings)
    bot = Bot(token=settings.require_bot_token())
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start_handler(message: Message) -> None:
        await message.answer(await handle_text("/start", services))

    @dispatcher.message()
    async def text_handler(message: Message) -> None:
        text = message.text or ""
        await message.answer(await handle_text(text, services))

    await dispatcher.start_polling(bot)
    return 0

## entry point
def main() -> int:
    """Run the requested application mode."""
    args = parse_args()
    if args.test is not None:
        return asyncio.run(run_test_mode(args.test))
    return asyncio.run(run_telegram_mode())


if __name__ == "__main__":
    sys.exit(main())
