"""Bot Kuis Telegram — main entry."""
import logging
import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

from bot import db
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

    # Auto-init DB + seed soal kalau masih kosong
    db.init_db()
    if db.soal_count() == 0:
        LOGGER.info("DB kosong — seeding soal...")
        import seed  # noqa: F401 — seed.py jalan sendiri pas diimport

        LOGGER.info("Seed selesai: %s soal", db.soal_count())

    app = ApplicationBuilder().token(token).build()
    for handler in get_handlers():
        app.add_handler(handler)

    LOGGER.info("Kuisbot started")
    app.run_polling()


if __name__ == "__main__":
    main()
