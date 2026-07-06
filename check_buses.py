import sqlite3, json, os

db = os.path.join(os.path.dirname(__file__), "database.db")
if not os.path.exists(db):
    print('NO_DB')
    raise SystemExit
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, plaque, current_lat, current_lon, dernier_arret FROM buses").fetchall()
print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
conn.close()
