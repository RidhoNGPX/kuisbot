"""Command & quiz handlers — mode RACE: ngetik jawaban manual, 15 detik, sesi 10-15 soal."""
import asyncio
import logging
import os
import random
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from bot import db

LOGGER = logging.getLogger(__name__)

# Sesi kuis aktif per chat
_sesi: dict[int, dict] = {}

SOAL_PER_SESI_MIN = 10
SOAL_PER_SESI_MAX = 15
WAKTU_SOAL = 15           # detik per soal
POIN_DASAR = 100
BONUS_WAKTU = 6           # poin ekstra per detik sisa


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
    return bool(update.effective_user) and update.effective_user.id == int(
        os.getenv("OWNER_ID", "0")
    )


def _esc(s: str) -> str:
    """Escape karakter MarkdownV2 di teks bebas."""
    for ch in "_*[]()~`>#+-=|{}.!":
        s = s.replace(ch, f"\\{ch}")
    return s


# ---------- commands ----------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "🎯 Kuisbot 🦫\n\n"
        "/kuis [kategori] — mulai kuis (sesi 10-15 soal)\n"
        "/kategori — daftar kategori\n"
        "/skor — skor kamu\n"
        "/leaderboard — top 10\n"
        "/stop — hentikan sesi\n\n"
        "⚡ Mode RACE: jawab dengan NGETIK jawabannya langsung (bukan huruf pilihan!). "
        "Waktu cuma 15 detik per soal — yang ngetik benar duluan, dapat poin terbesar!",
    )


async def kategori_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    daftar = db.kategori_list()
    if not daftar:
        await update.message.reply_text("Belum ada soal. Admin bisa /addsoal dulu 🦫")
        return
    await update.message.reply_text(
        "📚 Kategori:\n" + "\n".join(f"• {k}" for k in daftar)
    )


async def kuis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    if chat_id in _sesi:
        await update.message.reply_text("Sesi masih jalan! Tunggu selesai atau /stop 🦫")
        return

    kategori = " ".join(context.args).strip().lower() or None
    jumlah = random.randint(SOAL_PER_SESI_MIN, SOAL_PER_SESI_MAX)
    soal_list = db.ambil_soal_sesi(kategori, jumlah)
    if not soal_list:
        await update.message.reply_text(
            f"Belum ada soal{f' kategori {kategori}' if kategori else ''}. "
            "Coba /kategori buat lihat yang tersedia."
        )
        return

    _sesi[chat_id] = {
        "soal_list": soal_list,
        "index": -1,
        "skor_sesi": {},  # user_id: [nama, poin, benar]
        "host": update.effective_user.first_name if update.effective_user else "?",
    }
    await update.message.reply_text(
        f"🔥 SESI KUIS MULAI!\n"
        f"📚 {len(soal_list)} soal{f' — {kategori}' if kategori else ' — campuran'}\n"
        f"⏱️ {WAKTU_SOAL} detik per soal\n"
        f"✍️ Ketik jawabannya langsung!"
    )
    await asyncio.sleep(2)
    await _soal_berikutnya(context, chat_id)


async def _soal_berikutnya(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    sesi = _sesi.get(chat_id)
    if not sesi:
        return
    sesi["index"] += 1
    if sesi["index"] >= len(sesi["soal_list"]):
        await _akhiri_sesi(context, chat_id)
        return
    soal = sesi["soal_list"][sesi["index"]]
    teks = (
        f"❓ Soal {sesi['index'] + 1}/{len(sesi['soal_list'])}\n\n"
        f"{soal['pertanyaan']}\n\n"
        f"⏱️ {WAKTU_SOAL} detik — ngetik jawabannya langsung!"
    )
    msg = await context.bot.send_message(chat_id, teks)
    task = asyncio.create_task(_timeout(context, chat_id, soal["id"], msg.message_id))
    sesi.update({
        "soal": soal,
        "deadline": time.time() + WAKTU_SOAL,
        "task": task,
        "msg_id": msg.message_id,
    })


async def _timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int, soal_id: int, msg_id: int):
    await asyncio.sleep(WAKTU_SOAL)
    sesi = _sesi.get(chat_id)
    if not sesi or sesi.get("soal", {}).get("id") != soal_id:
        return
    soal = db.get_soal(soal_id)
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=(
                f"❓ Soal {sesi['index'] + 1}/{len(sesi['soal_list'])}\n\n"
                f"{soal['pertanyaan']}\n\n"
                f"⏰ Waktu habis! Jawaban: {soal['opsi_jawaban']}"
            ),
        )
    except Exception:
        pass
    await asyncio.sleep(2)
    await _soal_berikutnya(context, chat_id)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    sesi = _sesi.pop(chat_id, None)
    if sesi:
        if sesi.get("task"):
            sesi["task"].cancel()
        await update.message.reply_text("Sesi kuis dihentikan 🦫")
    else:
        await update.message.reply_text("Nggak ada sesi kuis yang jalan.")


async def skor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
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
    if not update.message:
        return
    rows = db.leaderboard(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("Leaderboard masih kosong. /kuis dulu! 🦫")
        return
    medal = ["🥇", "🥈", "🥉"]
    teks = "🏆 LEADERBOARD\n\n" + "\n".join(
        f"{medal[i] if i < 3 else f'{i + 1}.'} {r['nama']} — {r['poin']} poin"
        for i, r in enumerate(rows)
    )
    await update.message.reply_text(teks)


async def addsoal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not _admin(update):
        await update.message.reply_text("Owner only 🦫")
        return
    raw = update.message.text or ""
    if "\n" not in raw:
        await update.message.reply_text(
            "Format:\n"
            "/addsoal kategori | pertanyaan | jawaban_benar | opsi_lain1 | opsi_lain2 | opsi_lain3\n\n"
            "Contoh (jawaban benar ditulis duluan):\n"
            "/addsoal umum | Ibukota Indonesia? | Jakarta | Bandung | Surabaya | Medan"
        )
        return
    body = raw.split("\n", 1)[1].strip()
    parts = [p.strip() for p in body.split("|")]
    if len(parts) != 6:
        await update.message.reply_text(
            f"Harus 6 bagian dipisah `|`, kamu kasih {len(parts)} 🦫"
        )
        return
    kategori, pertanyaan, jawaban, o1, o2, o3 = parts
    if not all([kategori, pertanyaan, jawaban, o1, o2, o3]):
        await update.message.reply_text("Ada bagian yang kosong 🦫")
        return
    soal_id = db.add_soal(
        kategori.lower(), pertanyaan, jawaban, [o1, o2, o3],
        update.effective_user.id,
    )
    await update.message.reply_text(
        f"✅ Soal #{soal_id} tersimpan di kategori {kategori.lower()} 🦫"
    )


# ---------- jawaban (race mode) ----------


async def jawaban_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sesi = _sesi.get(chat_id)
    if not sesi or not update.message or "soal" not in sesi:
        return
    if time.time() > sesi["deadline"]:
        return

    teks = update.message.text.strip()
    if len(teks) < 2 or len(teks) > 60:
        return

    soal = sesi["soal"]
    kunci = soal["opsi_jawaban"].strip().lower()
    tebakan = " ".join(teks.lower().split()).strip("!?.,;:")
    if tebakan != kunci:
        return  # salah — biarkan pemain lain mencoba, jawaban tidak dibocorkan

    # BENAR & paling cepat!
    if sesi.get("task"):
        sesi["task"].cancel()
    _sesi.pop(chat_id, None)

    user = update.effective_user
    sisa = max(0, int(sesi["deadline"] - time.time()))
    poin = POIN_DASAR + sisa * BONUS_WAKTU
    streak = db.add_skor(chat_id, user.id, user.first_name, poin, benar=True)
    # sesi udah di-pop, simpan skor sesi manual buat rekap akhir
    sesi["skor_sesi"][user.id] = sesi["skor_sesi"].get(user.id, [user.first_name, 0, 0])
    sesi["skor_sesi"][user.id][1] += poin
    sesi["skor_sesi"][user.id][2] += 1
    _sesi[chat_id] = sesi
    bonus = f"\n🔥 Streak {streak}!" if streak >= 3 else ""
    await update.message.reply_text(
        f"⚡ {user.first_name} paling cepet! +{poin} poin (sisa {sisa}s){bonus}"
    )
    await asyncio.sleep(2)
    await _soal_berikutnya(context, chat_id)


# ---------- akhir sesi ----------


async def _akhiri_sesi(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    sesi = _sesi.pop(chat_id, None)
    if not sesi:
        return
    hasil = sorted(sesi["skor_sesi"].values(), key=lambda x: -x[1])
    if not hasil:
        await context.bot.send_message(
            chat_id, "Sesi selesai. Nggak ada yang jawab bener 😢🦫\n/kuis buat main lagi!"
        )
        return
    medal = ["🥇", "🥈", "🥉"]
    teks = "🏁 SESI SELESAI!\n\n" + "\n".join(
        f"{medal[i] if i < 3 else f'{i + 1}.'} {h[0]} — {h[1]} poin ({h[2]} benar)"
        for i, h in enumerate(hasil[:10])
    )
    teks += "\n\n/kuis buat main lagi 🦫"
    await context.bot.send_message(chat_id, teks)
