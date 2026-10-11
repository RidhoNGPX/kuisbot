"""Seed soal awal — jalan sekali: python seed.py"""
import json

from bot import db

db.init_db()

SOAL = [
    # kategori, pertanyaan, [4 opsi], index jawaban
    ("umum", "Ibukota Indonesia?", ["Jakarta", "Bandung", "Surabaya", "Medan"], 0),
    ("umum", "Planet terdekat dari Matahari?", ["Venus", "Merkurius", "Bumi", "Mars"], 1),
    ("umum", "Berapa sisi pada segitiga?", ["2", "3", "4", "5"], 1),
    ("umum", "Warna bendera Indonesia?", ["Merah-Putih", "Biru-Putih", "Merah-Hijau", "Putih-Hitam"], 0),
    ("umum", "Hewan tercepat di darat?", ["Singa", "Cheetah", "Kuda", "Jaguar"], 1),
    ("teknologi", "Kepanjangan dari CPU?", ["Central Process Unit", "Central Processing Unit", "Computer Personal Unit", "Central Program Utility"], 1),
    ("teknologi", "Bahasa pemrograman yang dibuat oleh Guido van Rossum?", ["Java", "Ruby", "Python", "Go"], 2),
    ("teknologi", "Perusahaan yang membuat Android?", ["Apple", "Microsoft", "Google", "Samsung"], 2),
    ("teknologi", "Kepanjangan dari HTML?", ["Hyper Text Markup Language", "High Text Machine Language", "Hyper Tabular Markup Language", "Home Tool Markup Language"], 0),
    ("game", "Karakter utama di seri game Mario?", ["Luigi", "Mario", "Wario", "Toad"], 1),
    ("game", "Game sandbox blok yang populer sejak 2011?", ["Terraria", "Roblox", "Minecraft", "Fortnite"], 2),
    ("game", "Di game Pokémon, tipe api lemah terhadap tipe?", ["Air", "Rumput", "Api", "Listrik"], 0),
    ("game", "Console Sony yang pertama?", ["PS2", "PSP", "PS1", "PS5"], 2),
    ("anime", "Tokoh utama Naruto?", ["Sasuke", "Naruto", "Sakura", "Kakashi"], 1),
    ("anime", "Anime tentang pemuda jadi Pemburu Iblis?", ["One Piece", "Demon Slayer", "Jujutsu Kaisen", "Chainsaw Man"], 1),
    ("anime", "Straw Hat adalah kelompok bajak laut di anime?", ["One Piece", "Naruto", "Bleach", "Fairy Tail"], 0),
    ("anime", "Pokémon pertama Ash di anime?", ["Pikachu", "Bulbasaur", "Charmander", "Squirtle"], 0),
]

for kategori, tanya, opsi, jw in SOAL:
    db.add_soal(kategori, tanya, opsi, jw, user_id=0)

print(f"Selesai — {len(SOAL)} soal di-seed.")
print(db.kategori_list())
