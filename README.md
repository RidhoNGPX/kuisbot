# kuisbot 🎯

Bot Kuis Telegram — multi kategori (umum, anime, game, teknologi), leaderboard, dan bank soal yang bisa ditambah langsung dari chat via `/addsoal`.

## Fitur

- `/start` — sapaan + info bot
- `/kuis [kategori]` — mulai sesi kuis (default: campuran)
- `/stop` — hentikan sesi kuis di chat
- `/skor` — lihat skor kamu
- `/leaderboard` — top 10 peringkat chat ini
- `/addsoal` — (admin) tambah soal baru via format teks
- `/kategori` — daftar kategori yang tersedia

### Mekanik
- Timer 30 detik per soal
- Yang jawab benar duluan dapat poin (cepat = poin lebih besar)
- Streak bonus: 3+ benar berturut-turut = poin ekstra
- Skor & streak persist di SQLite per user per chat

## Setup

```bash
cp config_sample.env .env   # isi BOT_TOKEN & OWNER_ID
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Deploy (systemd)

```ini
[Unit]
Description=Kuisbot Telegram
After=network.target

[Service]
WorkingDirectory=/opt/kuisbot
ExecStart=/opt/kuisbot/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

## Format /addsoal

```
/addsoal kategori | pertanyaan | opsiA | opsiB | opsiC | opsiD | huruf_jawaban
```

contoh:
```
/addsoal umum | Ibukota Indonesia? | Jakarta | Bandung | Surabaya | Medan | A
```
