import json
import sqlite3

from rapidfuzz import fuzz

DB = "data/unread.db"
FIELDS = ["category", "title", "summary", "deadline", "event_time", "venue",
          "eligibility", "how_to_apply", "submission_format", "link"]


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, title TEXT, summary TEXT,
            deadline TEXT, event_time TEXT, venue TEXT, eligibility TEXT,
            how_to_apply TEXT, submission_format TEXT, link TEXT,
            source_ids TEXT, seen_count INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS processed(id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, sender TEXT, timestamp TEXT, text TEXT);
        """)


def unprocessed(records):
    with conn() as c:
        done = {r["id"] for r in c.execute("SELECT id FROM processed")}
    return [r for r in records if r["id"] not in done]


def mark_processed(records):
    with conn() as c:
        c.executemany("INSERT OR IGNORE INTO processed(id) VALUES (?)",
                      [(r["id"],) for r in records])


def _same(row, it):
    if fuzz.token_set_ratio(row["title"], it["title"]) < 75:
        return False
    a, b = row["deadline"] or row["event_time"], it["deadline"] or it["event_time"]
    return a is None or b is None or a[:10] == b[:10]


def upsert(it):
    with conn() as c:
        for row in c.execute("SELECT * FROM items").fetchall():
            if _same(row, it):
                ids = sorted(set(json.loads(row["source_ids"])) | set(it["source_ids"]))
                updates = {f: (row[f] or it.get(f)) for f in FIELDS}  # fill gaps only
                sets = ", ".join(f"{k}=?" for k in updates)
                c.execute(f"UPDATE items SET {sets}, source_ids=?, seen_count=? WHERE id=?",
                          [*updates.values(), json.dumps(ids), len(ids), row["id"]])
                return "merged"
        vals = [it.get(f) for f in FIELDS]
        c.execute(f"INSERT INTO items({', '.join(FIELDS)}, source_ids, seen_count) "
                  f"VALUES ({', '.join('?' * len(FIELDS))}, ?, ?)",
                  [*vals, json.dumps(it["source_ids"]), len(it["source_ids"])])
        return "new"


def all_items():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM items ORDER BY COALESCE(deadline, event_time) IS NULL, COALESCE(deadline, event_time)")]
        
def save_messages(records):
    with conn() as c:
        c.executemany(
            "INSERT OR IGNORE INTO messages(id, sender, timestamp, text) VALUES (?,?,?,?)",
            [(r["id"], r["sender"], r["timestamp"], r["text"]) for r in records])


def get_messages(ids):
    if not ids:
        return []
    with conn() as c:
        q = ",".join("?" * len(ids))
        return [dict(r) for r in c.execute(
            f"SELECT sender, timestamp, text FROM messages WHERE id IN ({q}) ORDER BY timestamp", ids)]