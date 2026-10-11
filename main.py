"""Bot Kuis Telegram — main entry."""
import asyncio
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

from bot import db
from bot.handlers import get_handlers

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
LOGGER = logging.getLogger("kuisbot")

PROCESS_START = datetime.now()


async def post_init(application):
    """Notifikasi startup ke LOG_CHAT (kalau diisi di .env)."""
    log_chat = os.getenv("LOG_CHAT")
    if not log_chat:
        return
    try:
        await application.bot.send_message(
            chat_id=log_chat,
            text=(
                "🟢 kuisbot online!\n"
                f"📚 {db.soal_count()} soal siap\n"
                f"🕐 {PROCESS_START.strftime('%d %b %Y %H:%M')}"
            ),
        )
        LOGGER.info("Notifikasi startup terkirim ke LOG_CHAT")
    except Exception as e:
        LOGGER.warning("Gagal kirim notif startup ke LOG_CHAT: %s", e)


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

    app = ApplicationBuilder().token(token).post_init(post_init).build()
    for handler in get_handlers():
        app.add_handler(handler)

    LOGGER.info("Kuisbot started")
    app.run_polling()


if __name__ == "__main__":
    main()
