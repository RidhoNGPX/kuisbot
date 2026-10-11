"""Database layer — SQLite untuk soal, skor, dan sesi kuis."""
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
                opsi_jawaban TEXT NOT NULL,  -- teks jawaban benar (dibandingin persis, case-insensitive)
                opsi_lain TEXT NOT NULL,     -- JSON list opsi pengecoh
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
                PRIMARY KEY (chat_id, user_id)
            );
            """
        )


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
    import json

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
                "UPDATE skor SET poin=poin+?, benar=benar+1, streak=? "
                "WHERE chat_id=? AND user_id=?",
                (poin + bonus, streak, chat_id, user_id),
            )
            return streak
        c.execute(
            "UPDATE skor SET salah=salah+1, streak=0 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        return 0


def leaderboard(chat_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with _lock, _conn() as c:
        return c.execute(
            "SELECT nama, poin, benar, salah FROM skor WHERE chat_id=? "
            "ORDER BY poin DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()


def user_skor(chat_id: int, user_id: int) -> sqlite3.Row | None:
    with _lock, _conn() as c:
        return c.execute(
            "SELECT * FROM skor WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        ).fetchone()
