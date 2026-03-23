"""Bot entry point for Telegram mode and offline CLI test mode."""


from __future__ import annotations

##import libraries
import argparse
import asyncio
import sys

##import aiogram packages
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import load_settings
from handlers import handle_text
from services import ServiceContainer


def build_start_keyboard() -> InlineKeyboardMarkup:
    """Return inline buttons for common entry-point actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Available labs", callback_data="ask:what labs are available?"),
                InlineKeyboardButton(text="Backend health", callback_data="ask:/health"),
            ],
            [
                InlineKeyboardButton(text="Scores for lab 4", callback_data="ask:show me scores for lab-04"),
                InlineKeyboardButton(text="Top learners", callback_data="ask:who are the top 5 students?"),
            ],
        ]
    )


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
        await message.answer(
            await handle_text("/start", services),
            reply_markup=build_start_keyboard(),
        )

    @dispatcher.message()
    async def text_handler(message: Message) -> None:
        text = message.text or ""
        await message.answer(await handle_text(text, services))

    @dispatcher.callback_query()
    async def callback_handler(callback: CallbackQuery) -> None:
        data = callback.data or ""
        if not data.startswith("ask:"):
            await callback.answer("Unknown action.")
            return

        response = await handle_text(data[4:], services)
        await callback.message.answer(response)
        await callback.answer()

    await dispatcher.start_polling(bot)
    return 0


def main() -> int:
    """Run the requested application mode."""
    args = parse_args()
    if args.test is not None:
        return asyncio.run(run_test_mode(args.test))
    return asyncio.run(run_telegram_mode())


if __name__ == "__main__":
    sys.exit(main())
