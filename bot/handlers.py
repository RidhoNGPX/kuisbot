"""Command & quiz handlers — mode RACE + LOBBY.

Alur:
  /kuis [kategori]  (admin)  -> buka lobby 2 menit
  /ikutkuis                  -> user join lobby (min 2 orang)
  setelah 2 menit            -> kalau >=2 peserta: kuis mulai otomatis,
                                kalau kurang dari MIN_PESERTA: batal
  jawab = ngetik jawabannya langsung, 15 detik per soal,
  hanya peserta lobby yang bisa dapat poin.
"""
import asyncio
import logging
import os
import random
import re
import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from bot import db

LOGGER = logging.getLogger(__name__)

# State per chat:
#   {"fase": "lobby", ...} atau {"fase": "main", ...}
_sesi: dict[int, dict] = {}

LOBBY_DETIK = 120         # 2 menit
MIN_PESERTA = int(os.getenv("MIN_PESERTA", "2"))
SOAL_PER_SESI_MIN = 10
SOAL_PER_SESI_MAX = 15
WAKTU_SOAL = 15           # detik per soal
POIN_DASAR = 100
BONUS_WAKTU = 6           # poin ekstra per detik sisa


def get_handlers() -> list:
    return [
        CommandHandler("start", start),
        CommandHandler("kuis", kuis),
        CommandHandler("ikutkuis", ikutkuis),
        CommandHandler("stop", stop),
        CommandHandler("skor", skor),
        CommandHandler("leaderboard", leaderboard_cmd),
        CommandHandler("kategori", kategori_cmd),
        CommandHandler("addsoal", addsoal),
        CommandHandler("stat", stat_cmd),
        CommandHandler("badges", badges_cmd),
        MessageHandler(filters.TEXT & (~filters.COMMAND), jawaban_listener),
    ]


async def _admin_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False
    if user.id == int(os.getenv("OWNER_ID", "0")):
        return True
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, user.id
        )
        return member.status in ("administrator", "creator")
    except Exception:
        return False




def _nama(user) -> str:
    """Nama tampilan + mention: @username kalau ada, kalau tidak link by ID."""
    if user.username:
        return f"@{user.username}"
    return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

# ---------- commands ----------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "🎯 Kuisbot 🦫\n\n"
        "/kuis [kategori] — (admin) buka lobby kuis\n"
        "/ikutkuis — daftar ikut kuis\n"
        "/kategori — daftar kategori\n"
        "/skor — skor kamu\n"
        "/leaderboard — top 10\n"
        "/stat — statistik lengkap kamu\n"
        "/badges — koleksi badge\n"
        "/stop — (admin) hentikan sesi\n\n"
        "⚡ Cara main:\n"
        "1. Admin /kuis → lobby dibuka 2 menit\n"
        "2. Ketik /ikutkuis buat daftar (min 2 orang)\n"
        "3. Kuis mulai otomatis — ngetik jawabannya langsung!\n"
        "4. 15 detik per soal, yang benar duluan dapat poin terbesar"
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
    """(Admin) Buka lobby kuis."""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    if chat_id in _sesi:
        await update.message.reply_text(
            "Sesi/lobby masih jalan! Tunggu selesai atau /stop 🦫"
        )
        return
    if not await _admin_check(update, context):
        await update.message.reply_text("Khusus admin 🦫")
        return

    kategori = " ".join(context.args).strip().lower() or None
    if db.soal_count(kategori) < SOAL_PER_SESI_MIN:
        await update.message.reply_text(
            f"Soal{f' kategori {kategori}' if kategori else ''} kurang "
            f"(min {SOAL_PER_SESI_MIN}). Coba /kategori 🦫"
        )
        return

    user = update.effective_user
    _sesi[chat_id] = {
        "fase": "lobby",
        "kategori": kategori,
        "peserta": {user.id: (user.first_name, _nama(user))} if user else {},
        "host": user.first_name if user else "?",
        "host_id": user.id if user else 0,
        "mulai_task": None,
    }
    sisa_menit = LOBBY_DETIK // 60
    await update.message.reply_text(
        f"🔔 LOBBY KUIS DIBUKA!\n"
        f"📚 Kategori: {kategori or 'campuran'}\n"
        f"👤 Host: {user.first_name}\n\n"
        f"Ketik /ikutkuis buat gabung!\n"
        f"⏳ Lobby tutup {sisa_menit} menit lagi — min {MIN_PESERTA} orang "
        f"biar kuis jalan."
    )
    _sesi[chat_id]["mulai_task"] = asyncio.create_task(
        _lobby_countdown(context, chat_id)
    )


async def ikutkuis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    sesi = _sesi.get(chat_id)
    if not sesi or sesi.get("fase") != "lobby":
        await update.message.reply_text(
            "Nggak ada lobby yang buka. Admin bisa /kuis dulu 🦫"
        )
        return
    user = update.effective_user
    if user.id in sesi["peserta"]:
        await update.message.reply_text("Kamu udah terdaftar 😄")
        return
    sesi["peserta"][user.id] = (user.first_name, _nama(user))
    n = len(sesi["peserta"])
    sisa = max(0, int(LOBBY_DETIK - (time.time() - sesi.get("lobby_start", time.time()))))
    await update.message.reply_text(
        f"✅ {_nama(user)} ikut kuis! ({n} peserta)\n"
        f"⏳ sisa ~{sisa}s",
        parse_mode="HTML",
    )


async def _lobby_countdown(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    sesi = _sesi.get(chat_id)
    if not sesi:
        return
    sesi["lobby_start"] = time.time()
    # countdown 60s sekali di tengah
    await asyncio.sleep(LOBBY_DETIK - 60)
    sesi = _sesi.get(chat_id)
    if sesi and sesi["fase"] == "lobby":
        n = len(sesi["peserta"])
        tags = " ".join(p[1] for p in sesi["peserta"].values())
        await context.bot.send_message(
            chat_id,
            f"⏳ 1 MENIT LAGI! Baru {n} peserta.\n"
            f"{tags} — siap-siap! 🎯\n"
            f"Yang belum: /ikutkuis buruan!",
            parse_mode="HTML",
        )
    await asyncio.sleep(60)
    sesi = _sesi.get(chat_id)
    if not sesi or sesi["fase"] != "lobby":
        return
    if len(sesi["peserta"]) < MIN_PESERTA:
        _sesi.pop(chat_id, None)
        await context.bot.send_message(
            chat_id,
            f"😢 Lobby ditutup — peserta kurang dari {MIN_PESERTA} orang, "
            f"kuis batal.\n/kuis buat buka lobby lagi!",
        )
        return
    LOGGER.info("[lobby] mulai kuis: %d peserta", len(sesi["peserta"]))
    await _mulai_kuis(context, chat_id)


async def _mulai_kuis(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    sesi = _sesi.get(chat_id)
    if not sesi:
        return
    jumlah = random.randint(SOAL_PER_SESI_MIN, SOAL_PER_SESI_MAX)
    soal_list = db.ambil_soal_sesi(sesi["kategori"], jumlah)
    if not soal_list:
        _sesi.pop(chat_id, None)
        await context.bot.send_message(chat_id, "Soal kurang, kuis batal 🦫")
        return
    sesi.update({
        "fase": "main",
        "soal_list": soal_list,
        "index": -1,
        "skor_sesi": {uid: [p[1], 0, 0] for uid, p in sesi["peserta"].items()},
    })
    daftar = " ".join(p[1] for p in sesi["peserta"].values())
    await context.bot.send_message(
        chat_id,
        f"🔥 KUIS MULAI!\n"
        f"📚 {len(soal_list)} soal — ⏱️ {WAKTU_SOAL}s per soal\n"
        f"👥 {daftar}\n"
        f"✍️ Ngetik jawabannya langsung — gas!",
        parse_mode="HTML",
    )
    await asyncio.sleep(2)
    await _soal_berikutnya(context, chat_id)


async def _soal_berikutnya(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    sesi = _sesi.get(chat_id)
    if not sesi or sesi.get("fase") != "main":
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
    LOGGER.info("[soal] kirim soal %s/%s id=%s ke chat=%s", sesi["index"] + 1, len(sesi["soal_list"]), soal["id"], chat_id)
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
    soal_aktif = sesi.get("soal") if sesi else None
    if not sesi or soal_aktif is None or soal_aktif["id"] != soal_id:
        LOGGER.info("[timeout] skip: sesi udah gak cocok (chat=%s, soal=%s)", chat_id, soal_id)
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
    if not await _admin_check(update, context):
        await update.message.reply_text("Khusus admin 🦫")
        return
    chat_id = update.effective_chat.id
    sesi = _sesi.pop(chat_id, None)
    if sesi:
        if sesi.get("task"):
            sesi["task"].cancel()
        if sesi.get("mulai_task"):
            sesi["mulai_task"].cancel()
        await update.message.reply_text("Sesi kuis dihentikan 🦫")
    else:
        await update.message.reply_text("Nggak ada sesi kuis yang jalan.")


async def skor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    row = db.user_skor(update.effective_chat.id, update.effective_user.id)
    if not row:
        await update.message.reply_text("Kamu belum main. /ikutkuis dulu gas 🦫")
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
    if not await _admin_check(update, context):
        await update.message.reply_text("Khusus admin 🦫")
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


# ---------- jawaban (race mode, peserta lobby only) ----------


def _normalisasi(s: str) -> str:
    """Samakan bentuk jawaban & tebakan biar matching gak rewel."""
    s = s.lower().strip()
    s = s.strip("'\"“”‘’")              # kutip di ujung
    s = s.strip("!?.,;:")               # tanda baca di ujung
    s = re.sub(r"^(sekitar|kira-kira|kurang lebih|about)\s+", "", s)
    # buang gelar di awal
    s = re.sub(r"^(ir\.|hj\.|drs\.|prof\.|dr\.|ra\.)\s+", "", s)
    s = s.replace("-", " ")             # kupu-kupu == kupu kupu
    s = re.sub(r"[^a-z0-9\s]", "", s)   # buang sisa simbol
    s = " ".join(s.split())             # rapikan spasi
    return s


def _jawaban_cocok(tebakan: str, kunci: str) -> bool:
    """Matching santai: penuh, 1 kata kunci, cuplikan frasa, atau typo aman."""
    if not tebakan or not kunci:
        return False
    if tebakan == kunci:
        return True
    t_kata, k_kata = tebakan.split(), kunci.split()
    # 1 kata tebakan ada di kata kunci ('edison' utk 'thomas alva edison')
    if len(t_kata) == 1 and len(tebakan) >= 4 and tebakan in k_kata:
        return True
    # tebakan/cuplikan frasa masuk satu sama lain (jawaban panjang dicupin)
    if len(tebakan) >= 4 and (tebakan in kunci or kunci in tebakan):
        return True
    # semua kata tebakan (>=4 huruf) muncul di kunci ('thomas edison' utk 'thomas alva edison')
    kata_penting = [w for w in t_kata if len(w) >= 4]
    if kata_penting and all(w in k_kata for w in kata_penting):
        return True
    # typo: >=80% mirip dengan salah satu kata kunci
    import difflib
    if len(t_kata) == 1 and len(tebakan) >= 5:
        import difflib
        threshold = 0.85 if len(kunci) <= 8 else 0.8
        return difflib.SequenceMatcher(None, tebakan, max(k_kata, key=len)).ratio() >= threshold
    # frasa multi-kata: keseluruhan >=85% mirip
    return difflib.SequenceMatcher(None, tebakan, kunci).ratio() >= 0.85


async def jawaban_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sesi = _sesi.get(chat_id)
    if not sesi or not update.message or "soal" not in sesi:
        LOGGER.info("[listener] skip: gak ada sesi main (chat=%s)", chat_id)
        return
    if time.time() > sesi["deadline"]:
        LOGGER.info("[listener] skip: waktu habis (chat=%s)", chat_id)
        return
    user = update.effective_user
    if not user or user.id not in sesi["peserta"]:
        LOGGER.info("[listener] skip: %s bukan peserta (chat=%s)", user.id if user else "?", chat_id)
        return

    teks = update.message.text.strip()
    if len(teks) < 1 or len(teks) > 60:
        return

    soal = sesi["soal"]
    kunci = _normalisasi(soal["opsi_jawaban"])
    tebakan = _normalisasi(teks)
    LOGGER.info("[listener] tebakan %s: %r vs kunci %r", user.first_name, tebakan, kunci)
    cocok = _jawaban_cocok(tebakan, kunci)
    if not cocok:
        db.catat_jawaban(chat_id, user.id, soal["id"], soal["kategori"], False, WAKTU_SOAL)
        return  # salah — biarkan pemain lain mencoba

    # BENAR & paling cepat!
    if sesi.get("task"):
        sesi["task"].cancel()
    _sesi.pop(chat_id, None)

    sisa = max(0, int(sesi["deadline"] - time.time()))
    poin = POIN_DASAR + sisa * BONUS_WAKTU
    streak = db.add_skor(chat_id, user.id, user.first_name, poin, benar=True)
    db.catat_jawaban(chat_id, user.id, soal["id"], soal["kategori"], True, WAKTU_SOAL - sisa)
    if sisa >= WAKTU_SOAL - 3:  # jawab dalam <=3 detik
        db.catat_jawaban_kilat(chat_id, user.id)
    sesi["skor_sesi"][user.id] = sesi["skor_sesi"].get(user.id, [_nama(user), 0, 0])
    sesi["skor_sesi"][user.id][1] += poin
    sesi["skor_sesi"][user.id][2] += 1
    _sesi[chat_id] = sesi
    bonus = f"\n🔥 Streak {streak}!" if streak >= 3 else ""
    # cek badge baru
    badge_baru = db.badge_cek_dan_beri(chat_id, user.id, user.first_name)
    badge_txt = ""
    for b in badge_baru:
        badge_txt += f"\n🏅 Badge baru: {b['emoji']} {b['nama']}!"
    await update.message.reply_text(
        f"⚡ {_nama(user)} paling cepet! +{poin} poin (sisa {sisa}s){bonus}{badge_txt}",
        parse_mode="HTML",
    )
    await asyncio.sleep(2)
    await _soal_berikutnya(context, chat_id)


# ---------- akhir sesi ----------


async def _akhiri_sesi(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    sesi = _sesi.pop(chat_id, None)
    if not sesi:
        return
    hasil = sorted(sesi["skor_sesi"].values(), key=lambda x: -x[1])
    hasil = [h for h in hasil if h[1] > 0]
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
    # juara + badge
    juara_id = next(uid for uid, v in sesi["skor_sesi"].items() if v is hasil[0])
    db.catat_juara(chat_id, juara_id)
    badge_txt = ""
    for uid, v in sesi["skor_sesi"].items():
        for b in db.badge_cek_dan_beri(chat_id, uid, v[0].replace("@", "")):
            badge_txt += f"\n🏅 {b['emoji']} {v[0]} dapat badge {b['nama']}!"
    teks += badge_txt
    teks += "\n\n/kuis buat main lagi 🦫"
    await context.bot.send_message(chat_id, teks)


# ---------- statistik & badge ----------


async def stat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    st = db.stat_user(update.effective_chat.id, update.effective_user.id)
    if not st:
        await update.message.reply_text("Kamu belum main. /ikutkuis dulu 🦫")
        return
    teks = (
        f"📊 Statistik {st['nama']}\n\n"
        f"🏆 Rank: #{st['rank']} dari {st['total_pemain']} pemain\n"
        f"💎 Poin: {st['poin']}\n"
        f"✅ Benar: {st['benar']} | ❌ Salah: {st['salah']}\n"
        f"🎯 Winrate: {st['winrate']}%\n"
        f"🔥 Best streak: {st['best_streak']}\n"
        f"👑 Juara sesi: {st['juara']}x\n"
        f"⚡ Jawaban kilat (<3s): {st['jawaban_kilat']}x\n"
    )
    if st.get("rata_detik"):
        teks += f"⏱️ Rata-rata jawab: {st['rata_detik']}s\n"
    if st.get("kategori_kuat"):
        teks += f"💪 Terkuat: {st['kategori_kuat']}"
        if st.get("kategori_lemah"):
            teks += f" | 📚 Perlu belajar: {st['kategori_lemah']}"
    # badge count
    n_badge = len(db.badge_user(update.effective_chat.id, update.effective_user.id))
    teks += f"\n🏅 Badge: {n_badge}/{len(db.BADGES)} — /badges buat lihat"
    await update.message.reply_text(teks)


async def badges_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    punya = set(db.badge_user(chat_id, user_id))
    baris = []
    for key, b in db.BADGES.items():
        if key in punya:
            baris.append(f"{b['emoji']} {b['nama']} ✅")
        else:
            baris.append(f"🔲 {b['nama']} — {b['desc']}")
    teks = f"🏅 Koleksi Badge ({len(punya)}/{len(db.BADGES)})\n\n" + "\n".join(baris)
    await update.message.reply_text(teks)
