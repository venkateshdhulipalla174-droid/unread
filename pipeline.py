import sys

import db
from extract import extract
from ingest import parse_any

path = sys.argv[1]
default_date = sys.argv[2] if len(sys.argv) > 2 else None

db.init()
records = db.unprocessed(parse_any(path, default_date))
print(f"{len(records)} new messages")
if records:
    db.save_messages(records)
    stats = {"new": 0, "merged": 0}
    for it in extract(records):
        stats[db.upsert(it)] += 1
    db.mark_processed(records)
    print(stats)

print(f"\n{len(db.all_items())} items in database:")
for it in db.all_items():
    print(f"- [{it['category']}] {it['title']} | due {it['deadline']} | "
          f"event {it['event_time']} | seen in {it['seen_count']} msg(s)")