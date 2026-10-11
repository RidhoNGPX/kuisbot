"""Seed soal awal (mode race — jawaban teks) — jalan sekali: python seed.py"""
from bot import db

db.init_db()

SOAL = [
    # kategori, pertanyaan, jawaban_benar, [opsi pengecoh]
    ("umum", "Ibukota Indonesia?", "Jakarta", ["Bandung", "Surabaya", "Medan"]),
    ("umum", "Planet terdekat dari Matahari?", "Merkurius", ["Venus", "Bumi", "Mars"]),
    ("umum", "Berapa sisi pada segitiga?", "3", ["2", "4", "5"]),
    ("umum", "Hewan tercepat di darat?", "Cheetah", ["Singa", "Kuda", "Jaguar"]),
    ("umum", "Gunung tertinggi di Indonesia?", "Puncak Jaya", ["Semeru", "Rinjani", "Merapi"]),
    ("umum", "Danau terdalam di dunia?", "Baikal", ["Superior", "Toba", "Victoria"]),
    ("teknologi", "Bahasa pemrograman yang dibuat Guido van Rossum?", "Python", ["Java", "Ruby", "Go"]),
    ("teknologi", "Perusahaan yang membuat Android?", "Google", ["Apple", "Microsoft", "Samsung"]),
    ("teknologi", "Kepanjangan dari CPU?", "Central Processing Unit", ["Central Process Unit", "Computer Personal Unit", "Central Program Utility"]),
    ("teknologi", "Kernel open source buatan Linus Torvalds?", "Linux", ["Windows", "macOS", "Solaris"]),
    ("teknologi", "Perusahaan pembuat chip GPU RTX?", "Nvidia", ["AMD", "Intel", "Qualcomm"]),
    ("teknologi", "Protokol transfer halaman web yang aman?", "HTTPS", ["HTTP", "FTP", "SMTP"]),
    ("game", "Karakter utama seri game Mario?", "Mario", ["Luigi", "Wario", "Toad"]),
    ("game", "Game sandbox blok populer sejak 2011?", "Minecraft", ["Terraria", "Roblox", "Fortnite"]),
    ("game", "Di Pokémon, tipe api lemah terhadap tipe?", "Air", ["Rumput", "Api", "Listrik"]),
    ("game", "Konsol pertama buatan Sony?", "PS1", ["PS2", "PSP", "PS5"]),
    ("game", "Battle royale buatan Riot Games?", "Valorant", ["PUBG", "Apex Legends", "Free Fire"]),
    ("anime", "Tokoh utama Naruto?", "Naruto", ["Sasuke", "Sakura", "Kakashi"]),
    ("anime", "Anime tentang Pemburu Iblis dengan teknik pernapasan?", "Demon Slayer", ["One Piece", "Jujutsu Kaisen", "Chainsaw Man"]),
    ("anime", "Kelompok bajak laut Topi Jerami ada di anime?", "One Piece", ["Naruto", "Bleach", "Fairy Tail"]),
    ("anime", "Pokémon pertama Ash?", "Pikachu", ["Bulbasaur", "Charmander", "Squirtle"]),
    ("anime", "Tokoh utama Attack on Titan?", "Eren", ["Mikasa", "Armin", "Levi"]),
]

for kategori, tanya, jawaban, opsi_lain in SOAL:
    db.add_soal(kategori, tanya, jawaban, opsi_lain, user_id=0)

print(f"Selesai — {len(SOAL)} soal di-seed.")
print(db.kategori_list())
