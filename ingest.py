import os
import glob
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import re
import sys
import hashlib
from datetime import datetime, date

# Format A: 09/10/2026, 11:41 - Sender: text
RE_A = re.compile(r"^(\d{2}/\d{2}/\d{4}), (\d{2}:\d{2}) - ([^:]+):\s?(.*)$")
# Format B (your real paste): [11:41] Sender: text  (no date in the line)
RE_B = re.compile(r"^\[(\d{2}:\d{2})\] ([^:]+):\s?(.*)$")


def make_id(source, ts, sender, text):
    raw = f"{source}|{ts}|{sender}|{text}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def parse_whatsapp(path, default_date=None):
    """Return a list of {id, source, sender, timestamp, text, forwarded}.
    default_date (YYYY-MM-DD) is used only for lines that carry no date."""
    default_date = default_date or date.today().isoformat()
    records, current = [], None

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "---":
                continue

            m = RE_A.match(line)
            if m:
                d, t, sender, text = m.groups()
                ts = datetime.strptime(f"{d} {t}", "%d/%m/%Y %H:%M").isoformat()
            else:
                m = RE_B.match(line)
                if m:
                    t, sender, text = m.groups()
                    ts = datetime.fromisoformat(f"{default_date}T{t}:00").isoformat()

            if m:
                if current:
                    records.append(current)
                current = {"source": "whatsapp", "sender": sender.strip(),
                           "timestamp": ts, "text": text}
            elif current is not None:
                # no timestamp prefix = continuation of the previous message
                current["text"] += "\n" + line

    if current:
        records.append(current)

    for r in records:
        r["text"] = r["text"].strip()
        r["forwarded"] = "<Forwarded>" in r["text"] or "[Forwarded]" in r["text"]
        r["id"] = make_id(r["source"], r["timestamp"], r["sender"], r["text"])
    return records

def parse_eml(path):
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body else ""
    if body and body.get_content_type() == "text/html":
        text = re.sub(r"<[^>]+>", " ", text)  # crude tag strip
    text = re.sub(r"[ \t]+", " ", text).strip()[:3000]
    try:
        ts = parsedate_to_datetime(msg["Date"]).replace(tzinfo=None).isoformat()
    except Exception:
        ts = datetime.now().isoformat()
    sender = str(msg["From"] or "unknown")
    full = f"Subject: {msg['Subject']}\n{text}"
    return {"source": "email", "sender": sender, "timestamp": ts, "text": full,
            "forwarded": False, "id": make_id("email", ts, sender, full)}


def parse_any(path, default_date=None):
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.eml")))
        return sorted((parse_eml(p) for p in files), key=lambda r: r["timestamp"])
    if path.lower().endswith(".eml"):
        return [parse_eml(path)]
    return parse_whatsapp(path, default_date)
if __name__ == "__main__":
    path = sys.argv[1]
    default_date = sys.argv[2] if len(sys.argv) > 2 else None
    recs = parse_whatsapp(path, default_date)
    print(f"Parsed {len(recs)} messages\n")
    for r in recs[:5]:
        print(r["timestamp"], "|", r["sender"], "|", r["text"][:70].replace("\n", " / "))