"""Database layer — SQLite untuk soal, skor, sesi kuis, achievement, statistik."""
import json
import os
import sqlite3
import threading
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/kuisbot.db")
QUIZ_TIME = int(os.getenv("QUIZ_TIME", "30"))

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _lock, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS soal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kategori TEXT NOT NULL,
                pertanyaan TEXT NOT NULL,
                opsi_jawaban TEXT NOT NULL,
                opsi_lain TEXT NOT NULL,
                dibuat_oleh INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS skor (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                nama TEXT NOT NULL,
                poin INTEGER DEFAULT 0,
                benar INTEGER DEFAULT 0,
                salah INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                max_streak INTEGER DEFAULT 0,
                juara INTEGER DEFAULT 0,
                jawaban_kilat INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS achievement (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                badge TEXT NOT NULL,
                didapat_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (chat_id, user_id, badge)
            );
            CREATE TABLE IF NOT EXISTS log_jawaban (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                soal_id INTEGER NOT NULL,
                kategori TEXT NOT NULL,
                benar INTEGER NOT NULL,
                detik REAL NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            -- kolom tambahan utk DB lama
            """
        )
        # migrasi ringan: tambah kolom kalau belum ada
        existing = {r[1] for r in c.execute("PRAGMA table_info(skor)")}
        for col in ("best_streak", "max_streak", "juara", "jawaban_kilat"):
            if col not in existing:
                c.execute(f"ALTER TABLE skor ADD COLUMN {col} INTEGER DEFAULT 0")


def soal_count(kategori: str | None = None) -> int:
    with _lock, _conn() as c:
        if kategori:
            return c.execute(
                "SELECT COUNT(*) n FROM soal WHERE kategori=?", (kategori,)
            ).fetchone()["n"]
        return c.execute("SELECT COUNT(*) n FROM soal").fetchone()["n"]


def kategori_list() -> list[str]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT kategori, COUNT(*) n FROM soal GROUP BY kategori ORDER BY kategori"
        ).fetchall()
        return [f"{r['kategori']} ({r['n']} soal)" for r in rows]


def ambil_soal_sesi(kategori: str | None, jumlah: int) -> list[sqlite3.Row]:
    """Ambil N soal random untuk satu sesi (tanpa duplikat)."""
    with _lock, _conn() as c:
        if kategori:
            return c.execute(
                "SELECT * FROM soal WHERE kategori=? ORDER BY RANDOM() LIMIT ?",
                (kategori, jumlah),
            ).fetchall()
        return c.execute(
            "SELECT * FROM soal ORDER BY RANDOM() LIMIT ?", (jumlah,)
        ).fetchall()


def random_soal(kategori: str | None = None) -> sqlite3.Row | None:
    rows = ambil_soal_sesi(kategori, 1)
    return rows[0] if rows else None


def add_soal(
    kategori: str, pertanyaan: str, opsi_jawaban: str, opsi_lain: list[str], user_id: int
) -> int:
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO soal (kategori, pertanyaan, opsi_jawaban, opsi_lain, dibuat_oleh) "
            "VALUES (?,?,?,?,?)",
            (
                kategori,
                pertanyaan,
                opsi_jawaban,
                json.dumps(opsi_lain, ensure_ascii=False),
                user_id,
            ),
        )
        return cur.lastrowid or 0


def get_soal(soal_id: int) -> sqlite3.Row | None:
    with _lock, _conn() as c:
        return c.execute("SELECT * FROM soal WHERE id=?", (soal_id,)).fetchone()


def add_skor(chat_id: int, user_id: int, nama: str, poin: int, benar: bool) -> int:
    """Return streak baru."""
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO skor (chat_id, user_id, nama) VALUES (?,?,?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET nama=excluded.nama",
            (chat_id, user_id, nama),
        )
        if benar:
            row = c.execute(
                "SELECT streak FROM skor WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            ).fetchone()
            streak = (row["streak"] or 0) + 1
            bonus = streak * 2 if streak >= 3 else 0
            c.execute(
                "UPDATE skor SET poin=poin+?, benar=benar+1, streak=?, "
                "best_streak=MAX(best_streak, ?), max_streak=MAX(max_streak, ?) "
                "WHERE chat_id=? AND user_id=?",
                (poin + bonus, streak, streak, streak, chat_id, user_id),
            )
            return streak
        c.execute(
            "UPDATE skor SET salah=salah+1, streak=0 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        return 0


def catat_jawaban(chat_id: int, user_id: int, soal_id: int, kategori: str, benar: bool, detik: float):
    """Log tiap jawaban utk statistik."""
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO log_jawaban (chat_id, user_id, soal_id, kategori, benar, detik) "
            "VALUES (?,?,?,?,?,?)",
            (chat_id, user_id, soal_id, kategori, int(benar), detik),
        )


def catat_juara(chat_id: int, user_id: int):
    with _lock, _conn() as c:
        c.execute(
            "UPDATE skor SET juara=juara+1 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )


def catat_jawaban_kilat(chat_id: int, user_id: int):
    with _lock, _conn() as c:
        c.execute(
            "UPDATE skor SET jawaban_kilat=jawaban_kilat+1 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )


def leaderboard(chat_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with _lock, _conn() as c:
        return c.execute(
            "SELECT nama, poin, benar, salah, juara FROM skor WHERE chat_id=? "
            "ORDER BY poin DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()


def user_skor(chat_id: int, user_id: int) -> sqlite3.Row | None:
    with _lock, _conn() as c:
        return c.execute(
            "SELECT * FROM skor WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        ).fetchone()


# ---------- statistik ----------


def stat_user(chat_id: int, user_id: int) -> dict | None:
    """Statistik lengkap satu user di satu chat."""
    with _lock, _conn() as c:
        s = c.execute(
            "SELECT * FROM skor WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        ).fetchone()
        if not s:
            return None
        total = (s["benar"] or 0) + (s["salah"] or 0)
        winrate = round(100 * (s["benar"] or 0) / total) if total else 0
        # rank berdasarkan poin di chat ini
        rank = c.execute(
            "SELECT COUNT(*)+1 r FROM skor WHERE chat_id=? AND poin>?",
            (chat_id, s["poin"]),
        ).fetchone()["r"]
        # kategori terkuat & terlemah (min 3 jawaban biar valid)
        kat = c.execute(
            "SELECT kategori, SUM(benar) b, COUNT(*) t FROM log_jawaban "
            "WHERE chat_id=? AND user_id=? GROUP BY kategori HAVING t>=3 "
            "ORDER BY b*1.0/t DESC",
            (chat_id, user_id),
        ).fetchall()
        # kecepatan rata-rata saat benar
        rata = c.execute(
            "SELECT AVG(detik) d FROM log_jawaban WHERE chat_id=? AND user_id=? AND benar=1",
            (chat_id, user_id),
        ).fetchone()["d"]
        return {
            "nama": s["nama"],
            "poin": s["poin"],
            "benar": s["benar"],
            "salah": s["salah"],
            "winrate": winrate,
            "rank": rank,
            "total_pemain": c.execute(
                "SELECT COUNT(*) n FROM skor WHERE chat_id=?", (chat_id,)
            ).fetchone()["n"],
            "best_streak": s["best_streak"] or 0,
            "juara": s["juara"] or 0,
            "jawaban_kilat": s["jawaban_kilat"] or 0,
            "kategori_kuat": kat[0]["kategori"] if kat else None,
            "kategori_lemah": kat[-1]["kategori"] if len(kat) >= 2 else None,
            "rata_detik": round(rata, 1) if rata else None,
        }


# ---------- achievement ----------

# Definisi badge: key -> (emoji, nama, deskripsi, fungsi cek)
# cek menerima (stat: dict, konteks: dict) -> bool
BADGES: dict[str, dict] = {
    "first_win": {
        "emoji": "🌟", "nama": "Langkah Pertama",
        "desc": "Jawab benar pertama kali",
        "cek": lambda st, ctx: st["benar"] >= 1,
    },
    "streak5": {
        "emoji": "🔥", "nama": "Streak Master",
        "desc": "Streak 5 benar berturut-turut",
        "cek": lambda st, ctx: st["best_streak"] >= 5,
    },
    "streak10": {
        "emoji": "☄️", "nama": "Tidak Terhentikan",
        "desc": "Streak 10 benar berturut-turut",
        "cek": lambda st, ctx: st["best_streak"] >= 10,
    },
    "kilat": {
        "emoji": "⚡", "nama": "Speed Demon",
        "desc": "Jawab benar di bawah 3 detik (3x)",
        "cek": lambda st, ctx: st["jawaban_kilat"] >= 3,
    },
    "juara1": {
        "emoji": "🏆", "nama": "Champion",
        "desc": "Juara 1 sesi kuis",
        "cek": lambda st, ctx: st["juara"] >= 1,
    },
    "juara5": {
        "emoji": "👑", "nama": "Raja Kuis",
        "desc": "Juara 5 sesi kuis",
        "cek": lambda st, ctx: st["juara"] >= 5,
    },
    "poin1000": {
        "emoji": "💎", "nama": "Kolektor Poin",
        "desc": "Kumpulkan 1.000 poin",
        "cek": lambda st, ctx: st["poin"] >= 1000,
    },
    "poin5000": {
        "emoji": "🖤", "nama": "Legenda Kolam",
        "desc": "Kumpulkan 5.000 poin",
        "cek": lambda st, ctx: st["poin"] >= 5000,
    },
    "sniper": {
        "emoji": "🎯", "nama": "Penembak Jitu",
        "desc": "Winrate 80%+ (min 20 jawaban)",
        "cek": lambda st, ctx: st["benar"] + st["salah"] >= 20 and st["winrate"] >= 80,
    },
    "rajageo": {
        "emoji": "🗺️", "nama": "Penjelajah",
        "desc": "Benar 10+ di kategori geografi",
        "cek": lambda st, ctx: ctx.get("geo_benar", 0) >= 10,
    },
}


def badge_cek_dan_beri(chat_id: int, user_id: int, nama: str) -> list[dict]:
    """Cek semua badge; simpan yang baru; return list badge baru didapat."""
    st = stat_user(chat_id, user_id)
    if not st:
        return []
    # konteks tambahan (kategori spesifik)
    with _lock, _conn() as c:
        geo = c.execute(
            "SELECT SUM(benar) b FROM log_jawaban WHERE chat_id=? AND user_id=? AND kategori='geografi'",
            (chat_id, user_id),
        ).fetchone()["b"]
    ctx = {"geo_benar": geo or 0}

    with _lock, _conn() as c:
        punya = {
            r["badge"]
            for r in c.execute(
                "SELECT badge FROM achievement WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
        }
        c.execute(
            "INSERT INTO achievement (chat_id, user_id, badge) VALUES (?,?,?) "
            "ON CONFLICT DO NOTHING",
            (chat_id, user_id, "__init__"),  # noop placeholder utk pastikan tabel ada
        ) if False else None
        baru = []
        for key, b in BADGES.items():
            if key in punya:
                continue
            try:
                if b["cek"](st, ctx):
                    c.execute(
                        "INSERT OR IGNORE INTO achievement (chat_id, user_id, badge) VALUES (?,?,?)",
                        (chat_id, user_id, key),
                    )
                    baru.append({"key": key, **b})
            except Exception:
                continue
        return baru


def badge_user(chat_id: int, user_id: int) -> list[str]:
    with _lock, _conn() as c:
        return [
            r["badge"]
            for r in c.execute(
                "SELECT badge FROM achievement WHERE chat_id=? AND user_id=? ORDER BY didapat_at",
                (chat_id, user_id),
            )
        ]
