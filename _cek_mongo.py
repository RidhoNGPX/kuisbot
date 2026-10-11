
import pymongo
# cluster sekarang resolve (SRV ketemu: ac-annraob-shard-00-0x) tapi SSL handshake gagal
# coba 1: tlsAllowInvalidCertificates (diagnosa saja)
uri = "mongodb+srv://ridhokepret0900_db_user:kLSDj78aXXhyeuaX@teledatabase.3etik7b.mongodb.net/?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true&serverSelectionTimeoutMS=15000"
try:
    c = pymongo.MongoClient(uri)
    print("DBs (tls lax):", c.list_database_names())
except Exception as e:
    print("gagal juga:", type(e).__name__, str(e)[:200])
