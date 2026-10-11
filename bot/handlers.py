"""Command & quiz handlers."""
import asyncio
import json
import logging
import random
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import db

LOGGER = logging.getLogger(__name__)

# Sesi kuis aktif per chat: {chat_id: {"soal": row, "deadline": ts, "task": asyncio.Task}}
_sesi: dict[int, dict] = {}

POIN_DASAR = 100


def get_handlers() -> list:
    return [
        CommandHandler("start", start),
        CommandHandler("kuis", kuis),
        CommandHandler("stop", stop),
        CommandHandler("skor", skor),
        CommandHandler("leaderboard", leaderboard_cmd),
        CommandHandler("kategori", kategori_cmd),
        CommandHandler("addsoal", addsoal),
        MessageHandler(filters.TEXT & (~filters.COMMAND), jawaban_listener),
    ]


def _admin(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == int(
        __import__("os").getenv("OWNER_ID", "0")
    )


# ---------- commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 *Kuisbot* 🦫\n\n"
        "/kuis \\[kategori\\] — mulai kuis\n"
        "/kategori — daftar kategori\n"
        "/skor — skor kamu\n"
        "/leaderboard — top 10\n"
        "/stop — hentikan sesi\n\n"
        "Jawab dengan mengetik A/B/C/D. Yang cepat dan benar, dia yang dapat poin besar!",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def kategori_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    daftar = db.kategori_list()
    if not daftar:
        await update.message.reply_text("Belum ada soal. Admin bisa /addsoal dulu 🦫")
        return
    await update.message.reply_text(
        "📚 Kategori:\n" + "\n".join(f"• {k}" for k in daftar)
    )


async def kuis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in _sesi:
        await update.message.reply_text("Masih ada sesi kuis jalan! /stop dulu kalau mau ganti 🦫")
        return

    kategori = " ".join(context.args).strip() or None
    soal = db.random_soal(kategori)
    if not soal:
        await update.message.reply_text(
            f"Belum ada soal{f' kategori {kategori}' if kategori else ''}. "
            "Coba /kategori buat lihat yang tersedia."
        )
        return
    await _kirim_soal(update, context, chat_id, soal)


async def _kirim_soal(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, soal):
    opsi = json.loads(soal["opsi"])
    abjad = "ABCD"
    teks = (
        f"🎯 *KUIS* — {soal['kategori'].upper()}\n\n"
        f"{soal['pertanyaan']}\n\n"
        + "\n".join(f"{abjad[i]}. {o}" for i, o in enumerate(opsi))
        + f"\n\n⏱️ {db.QUIZ_TIME} detik!"
    )
    msg = await context.bot.send_message(chat_id, teks, parse_mode=ParseMode.MARKDOWN_V2)
    deadline = time.time() + db.QUIZ_TIME
    task = asyncio.create_task(_timeout(update, context, chat_id, soal["id"], msg.message_id))
    _sesi[chat_id] = {"soal": soal, "deadline": deadline, "task": task, "msg_id": msg.message_id}


async def _timeout(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, soal_id: int, msg_id: int):
    await asyncio.sleep(db.QUIZ_TIME)
    sesi = _sesi.get(chat_id)
    if not sesi or sesi["soal"]["id"] != soal_id:
        return
    _sesi.pop(chat_id, None)
    soal = db.get_soal(soal_id)
    abjad = "ABCD"
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=(
                f"⏰ Waktu habis!\n\nJawaban yang benar: *{abjad[soal['jawaban']]}. "
                f"{json.loads(soal['opsi'])[soal['jawaban']]}*\n\nKetik /kuis buat main lagi 🦫"
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception:
        pass


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sesi = _sesi.pop(chat_id, None)
    if sesi:
        sesi["task"].cancel()
        await update.message.reply_text("Sesi kuis dihentikan 🦫")
    else:
        await update.message.reply_text("Nggak ada sesi kuis yang jalan.")


async def skor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = db.user_skor(update.effective_chat.id, update.effective_user.id)
    if not row:
        await update.message.reply_text("Kamu belum main. /kuis dulu gas 🦫")
        return
    await update.message.reply_text(
        f"📊 Skor {row['nama']}:\n"
        f"• Poin: {row['poin']}\n"
        f"• Benar: {row['benar']} | Salah: {row['salah']}\n"
        f"• Streak: {row['streak']} 🔥"
    )


async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.leaderboard(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("Leaderboard masih kosong. /kuis dulu! 🦫")
        return
    medal = ["🥇", "🥈", "🥉"]
    teks = "🏆 *LEADERBOARD*\n\n" + "\n".join(
        f"{medal[i] if i < 3 else f'{i+1}.'} {r['nama']} — {r['poin']} poin"
        for i, r in enumerate(rows)
    )
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN_V2)


async def addsoal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update):
        await update.message.reply_text("Owner only 🦫")
        return
    raw = update.message.text
    if not raw or "\n" not in raw:
        await update.message.reply_text(
            "Format:\n```\n/addsoal kategori | pertanyaan | opsiA | opsiB | opsiC | opsiD | A\n```",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    # /addsoal pertanyaan di baris pertama, isi di baris-baris berikutnya
    body = raw.split("\n", 1)[1].strip()
    parts = [p.strip() for p in body.split("|")]
    if len(parts) != 7:
        await update.message.reply_text(
            f"Harus 7 bagian dipisah `|`, kamu kasih {len(parts)}. 🦫"
        )
        return
    kategori, pertanyaan, *opsi_jawaban = parts
    opsi = opsi_jawaban[:4]
    jw = opsi_jawaban[4].upper()
    if jw not in "ABCD" or len(jw) != 1:
        await update.message.reply_text("Jawaban harus huruf A/B/C/D 🦫")
        return
    soal_id = db.add_soal(kategori.lower(), pertanyaan, opsi, "ABCD".index(jw),
                           update.effective_user.id)
    await update.message.reply_text(f"✅ Soal #{soal_id} tersimpan di kategori *{kategori.lower()}* 🦫",
                                    parse_mode=ParseMode.MARKDOWN_V2)


# ---------- jawaban ----------

async def jawaban_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sesi = _sesi.get(chat_id)
    if not sesi or not update.message:
        return
    teks = update.message.text.strip().upper()
    if teks not in "ABCD" or len(teks) != 1:
        return
    if time.time() > sesi["deadline"]:
        return

    soal = sesi["soal"]
    user = update.effective_user
    if teks == "ABCD"[soal["jawaban"]]:
        _sesi.pop(chat_id, None)
        sesi["task"].cancel()
        sisa = max(0, int(sesi["deadline"] - time.time()))
        poin = POIN_DASAR + sisa * 3
        streak = db.add_skor(chat_id, user.id, user.first_name, poin, benar=True)
        bonus = f"\n🔥 Streak {streak}! Bonus aktif." if streak >= 3 else ""
        await update.message.reply_text(
            f"✅ *{user.first_name}* bener! +{poin} poin "
            f"(sisa {sisa}s){bonus}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        # auto lanjut kalau di grup
        if update.effective_chat.type in ("group", "supergroup"):
            await asyncio.sleep(3)
            if chat_id not in _sesi:
                soal_baru = db.random_soal(soal["kategori"])
                if soal_baru:
                    await _kirim_soal(update, context, chat_id, soal_baru)
    else:
        db.add_skor(chat_id, user.id, user.first_name, 0, benar=False)
        # salah: biar orang lain masih bisa jawab, jangan bongkar jawaban
