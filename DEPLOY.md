# Deploy kuisbot di VPS (Ubuntu)

## 1. Clone & setup

```bash
git clone https://github.com/RidhoNGPX/kuisbot.git
cd kuisbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Kalau VPS-nya belum punya python3.10+: `sudo apt update && sudo apt install python3 python3-venv -y`

## 2. Bikin bot token

1. Chat [@BotFather](https://t.me/BotFather) → `/newbot`
2. Simpan token-nya

Dapetin ID kamu: chat [@userinfobot](https://t.me/userinfobot) → dia balas ID kamu (angka).

## 3. Config

```bash
cp config_sample.env .env
nano .env
```

Isi:
```env
BOT_TOKEN=123456:ABCdefGHI...
OWNER_ID=id_kamu
DB_PATH=data/kuisbot.db
```

## 4. Seed soal (sekali aja)

```bash
*(tidak perlu — seed otomatis saat bot pertama kali jalan)*
```

## 5. Tes manual dulu

```bash
python main.py
```

Buka Telegram → DM bot kamu → `/start`. Kalau balas, beres. `Ctrl+C` buat stop.

## 6. Jalanin sebagai service (systemd)

```bash
sudo nano /etc/systemd/system/kuisbot.service
```

Isi (ganti `namakamu` sesuai user VPS):

```ini
[Unit]
Description=Kuisbot Telegram
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=namakamu
WorkingDirectory=/home/namakamu/kuisbot
ExecStart=/home/namakamu/kuisbot/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Aktifin:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kuisbot
sudo systemctl status kuisbot   # harus "active (running)"
```

## Perintah harian

```bash
sudo systemctl restart kuisbot   # restart (misal habis edit .env)
sudo systemctl stop kuisbot      # stop
journalctl -u kuisbot -f         # lihat log live
```

## Update bot nanti

```bash
cd ~/kuisbot
git pull
sudo systemctl restart kuisbot
```

## Troubleshooting cepat

| Gejala | Cek |
|---|---|
| Bot gak online | `journalctl -u kuisbot -n 50` — biasanya BOT_TOKEN salah |
| Kuis gak mulai | Pastikan yang `/kuis` adalah admin grup / sesuai OWNER_ID |
| Gak ada peserta | Min 2 orang `/ikutkuis` sebelum lobby habis |
| DB error | `python seed.py` sekali lagi (DB hilang kalau folder data kehapus) |
