"""Bot Kuis Telegram — main entry."""
import logging
import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

from bot.handlers import get_handlers

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
LOGGER = logging.getLogger("kuisbot")


def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN belum diisi di .env")

    app = ApplicationBuilder().token(token).build()
    for handler in get_handlers():
        app.add_handler(handler)

    LOGGER.info("Kuisbot started")
    app.run_polling()


if __name__ == "__main__":
    main()
