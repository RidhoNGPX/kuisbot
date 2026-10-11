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
    # --- tambahan umum ---
    ("umum", "Ibukota Jepang?", "Tokyo", ["Osaka", "Kyoto", "Seoul"]),
    ("umum", "Berapa jumlah provinsi Indonesia saat ini?", "38", ["34", "36", "40"]),
    ("umum", "Benua terluas di dunia?", "Asia", ["Afrika", "Amerika", "Eropa"]),
    ("umum", "Laut terluas di dunia?", "Pasifik", ["Atlantik", "Hindia", "Arktik"]),
    ("umum", "Kerajaan Hindu terbesar di Indonesia?", "Majapahit", ["Sriwijaya", "Mataram", "Kutai"]),
    ("umum", "Proklamasi kemerdekaan Indonesia tahun?", "1945", ["1944", "1946", "1950"]),
    ("umum", "Candi borobudur ada di provinsi?", "Jawa Tengah", ["Jawa Timur", "DI Yogyakarta", "Jawa Barat"]),
    ("umum", "Satuan kimia untuk besi?", "Fe", ["Au", "Ag", "Cu"]),
    ("umum", "Air mendidih pada suhu berapa derajat celsius di permukaan laut?", "100", ["90", "110", "120"]),
    ("umum", "Hewan darat terbesar di dunia?", "Gajah", ["Jerapah", "Badak", "Kuda Nil"]),
    ("umum", "Buah dengan vitamin C paling tinggi dari daftar ini?", "Jeruk", ["Pisang", "Semangka", "Alpukat"]),
    ("umum", "Berapa menit dalam satu jam?", "60", ["30", "90", "100"]),
    # --- tambahan teknologi ---
    ("teknologi", "Bahasa pemrograman yang jalan di browser?", "JavaScript", ["Python", "Java", "C++"]),
    ("teknologi", "Kepanjangan dari WWW?", "World Wide Web", ["World Web Wide", "Wide World Web", "Web World Wide"]),
    ("teknologi", "Perusahaan yang membuat iPhone?", "Apple", ["Samsung", "Xiaomi", "Google"]),
    ("teknologi", "Bahasa styling untuk halaman web?", "CSS", ["HTML", "SQL", "JSON"]),
    ("teknologi", "Sistem kontrol versi paling populer?", "Git", ["SVN", "Mercurial", "Perforce"]),
    ("teknologi", "Hacker berbaju putih yang mencari celah keamanan secara legal?", "White Hat", ["Black Hat", "Grey Hat", "Red Hat"]),
    ("teknologi", "Teknologi AI buatan OpenAI yang terkenal?", "ChatGPT", ["Claude", "Gemini", "Copilot"]),
    ("teknologi", "Satuan penyimpanan data terbesar dari daftar ini?", "Terabyte", ["Gigabyte", "Megabyte", "Kilobyte"]),
    ("teknologi", "Perintah untuk melihat isi direktori di terminal Linux?", "ls", ["cd", "pwd", "mv"]),
    ("teknologi", "Perusahaan teknologi yang punya Google Chrome?", "Google", ["Mozilla", "Microsoft", "Opera"]),
    # --- tambahan game ---
    ("game", "Hijau adalah warna khas karakter Nintendo bernama?", "Luigi", ["Mario", "Yoshi", "Peach"]),
    ("game", "Dota 2 dan CS2 berada di platform distribusi game bernama?", "Steam", ["Epic Games", "GOG", "Origin"]),
    ("game", "Game mobil MOBA populer buatan Moonton?", "Mobile Legends", ["Free Fire", "PUBG Mobile", "CODM"]),
    ("game", "Karakter berpedang biru di Tekken yang jadi rival Kazuya?", "Jin", ["Heihachi", "Law", "Paul"]),
    ("game", "Pokémon kijang api generasi 1 bernama?", "Charmander", ["Squirtle", "Bulbasaur", "Pidgey"]),
    ("game", "FPS taktis Valve dengan bom dan defuse di peta Dust2?", "Counter Strike", ["Valorant", "Overwatch", "Apex Legends"]),
    ("game", "Roblox awalnya dirilis tahun?", "2006", ["2001", "2010", "2014"]),
    # --- tambahan anime ---
    ("anime", "Pengguna Gura Gura no Mi di One Piece?", "Whitebeard", ["Luffy", "Kaido", "Zoro"]),
    ("anime", "Sekolah penyihir di anime Harry Potter... eh, petualangan penyihir buatan J.K. terletak di negara?", "Inggris", ["Amerika", "Jepang", "Prancis"]),
    ("anime", "Istri Tetsuya di Fairy Tail... eh, tokoh utama Fairy Tail bernama?", "Natsu", ["Gray", "Erza", "Gajeel"]),
    ("anime", "Anime mecha populer dengan unit EVA-01?", "Evangelion", ["Gundam", "Code Geass", "Gurren Lagann"]),
    ("anime", "Karakter kambing biru di anime populer yang suka menjelaskan kekuatan baru musuh?", "Vegeta", ["Goku", "Piccolo", "Frieza"]),
    ("anime", "Gon dan Killua adalah tokoh utama anime?", "Hunter x Hunter", ["One Piece", "My Hero Academia", "Black Clover"]),
    ("anime", "Layar tancap: anime tentang catur dunia antara Sora dan Shiro?", "No Game No Life", ["Kaguya-sama", "Spy x Family", "Horimiya"]),
]

for kategori, tanya, jawaban, opsi_lain in SOAL:
    db.add_soal(kategori, tanya, jawaban, opsi_lain, user_id=0)

print(f"Selesai — {len(SOAL)} soal di-seed.")
print(db.kategori_list())
