import json
import re
import sys
from datetime import datetime, timedelta

import dateparser
from dateparser.search import search_dates
import ollama

from ingest import parse_whatsapp

MODEL = "qwen2.5:7b-instruct"
MAX_CHARS = 2500  # per chunk, keeps prompt + answer inside the 4096 context

STR = {"type": "string"}
SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": [
                        "tech_event", "assessment", "non_tech_event",
                        "club_inauguration", "academic_task", "admin", "other"]},
                    "title": STR,
                    "summary": STR,
                    "deadline_text": STR,
                    "event_time_text": STR,
                    "venue": STR,
                    "eligibility": STR,
                    "how_to_apply": STR,
                    "submission_format": STR,
                    "link": STR,
                    "source_msgs": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["category", "title", "summary", "deadline_text",
                             "event_time_text", "venue", "eligibility",
                             "how_to_apply", "submission_format", "link",
                             "source_msgs"],
            },
        }
    },
    "required": ["items"],
}

SYSTEM = """You extract actionable items for college students from chat messages.
Each message is numbered like [3] with its timestamp.

Categories:
- tech_event: hackathons, workshops, coding contests, technical talks
- assessment: assignments, projects, submissions, exams given by faculty
- non_tech_event: cultural, sports, social, awareness or charity events
- club_inauguration: club or chapter launches and inaugurations
- academic_task: mandatory course or placement tasks (registrations, account setup, platform enrolment)
- admin: surveys, forms, general notices from the institute
- other: anything else actionable

Rules:
- Extract only things a student may need to act on or attend. Ignore chatter, thanks, acknowledgements and attachment-only lines (file names).
- Ignore messages meant for staff or coordinators, not students.
- A forwarded or quoted copy of a message is the same item. If the SAME item appears in several messages, output it ONCE, list ALL message numbers in source_msgs, and keep extra details from later messages.
- Different required actions are SEPARATE items, even if they come from the same sender or topic. If one message or one sender asks for two different steps (for example one fix and one new registration), output two items.
- For events: put the full date AND time in event_time_text. Leave deadline_text empty for events unless there is a separate registration deadline.
- For assignments, tasks and surveys: copy the deadline phrase from the message into deadline_text, exactly as written.
- NEVER convert or calculate dates yourself.
- Never invent details. Use "" for anything not stated.
- eligibility: fill it ONLY if the message explicitly names who it applies to (a year, semester, branch, or group). If the message only says "Dear students" or names no audience, use ""."""

def make_chunks(records):
    chunks, cur, size = [], [], 0
    for i, r in enumerate(records, 1):
        if len(r["text"]) < 20:  # cheap prefilter: "ok sir", "thanks"
            continue
        block = f"[{i}] ({r['timestamp'][:16]}) {r['sender']}: {r['text']}"
        if cur and size + len(block) > MAX_CHARS:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(block)
        size += len(block)
    if cur:
        chunks.append(cur)
    return chunks


ISO = re.compile(r"^\d{4}-\d{2}-\d{2}")
CUE = re.compile(
    r"(?:on or before|before|by|till|until|due(?: on| by)?|last date(?: is|:)?)\s+([^.\n,;]{3,40})",
    re.I,
)

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY = re.compile(r"\b(" + "|".join(DAYS) + r")\b", re.I)


def weekday_date(text, base_iso):
    """'by next Wednesday' / 'by Sunday' -> the first such weekday after the message date."""
    m = WEEKDAY.search(text)
    if not m or re.search(r"\d", text):
        return None
    base = datetime.fromisoformat(base_iso)
    delta = (DAYS.index(m.group(1).lower()) - base.weekday()) % 7 or 7
    day = base + timedelta(days=delta)
    return day.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="minutes")
def resolve(text, base_iso):
    if not text:
        return None
    text = text.strip()
    if ISO.match(text):  # model returned an ISO date despite instructions
        try:
            return datetime.fromisoformat(text).isoformat(timespec="minutes")
        except ValueError:
            pass
    w = weekday_date(text, base_iso)
    if w:
        return w
    settings = {
        "RELATIVE_BASE": datetime.fromisoformat(base_iso),
        "PREFER_DATES_FROM": "future",
        "DATE_ORDER": "DMY",
    }
    cleaned = re.sub(r"^(on or before|before|by|till|until|on)\s+", "", text, flags=re.I)
    d = dateparser.parse(cleaned, settings=settings)
    if d:
        return d.isoformat(timespec="minutes")
    if len(text) > 25:  # model returned a sentence: look for a date inside it
        found = search_dates(text, settings=settings)
        if found:
            return found[0][1].isoformat(timespec="minutes")
    return None


def find_deadline(texts, base_iso):
    """Fallback: scan the original messages for 'by/before/due ...' phrases."""
    for t in texts:
        for m in CUE.finditer(t):
            d = resolve(m.group(1), base_iso)
            if d:
                return m.group(1).strip(), d
    return "", None


def extract(records):
    results = []
    chunks = make_chunks(records)
    for n, chunk in enumerate(chunks, 1):
        print(f"Chunk {n}/{len(chunks)} ...", flush=True)
        resp = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": "\n\n".join(chunk)},
            ],
            format=SCHEMA,
            options={"temperature": 0, "num_ctx": 4096},
        )
        try:
            items = json.loads(resp["message"]["content"])["items"]
        except (json.JSONDecodeError, KeyError):
            print("  ! bad JSON from model, skipping chunk")
            continue
        for it in items:
            src = [i for i in it["source_msgs"] if 1 <= i <= len(records)]
            base = records[src[0] - 1]["timestamp"] if src else records[0]["timestamp"]
            it["deadline"] = resolve(it["deadline_text"], base)
            it["event_time"] = resolve(it["event_time_text"], base)
            if it["deadline"] is None and it["category"] != "non_tech_event":
                texts = [records[i - 1]["text"] for i in src]
                it["deadline_text"], it["deadline"] = find_deadline(texts, base)
            it["source_ids"] = [records[i - 1]["id"] for i in src]
            results.append(it)
    return results


if __name__ == "__main__":
    path = sys.argv[1]
    default_date = sys.argv[2] if len(sys.argv) > 2 else None
    records = parse_whatsapp(path, default_date)
    items = extract(records)
    with open("data/extracted.json", "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"\n{len(items)} items\n")
    for it in items:
        print(f"[{it['category']}] {it['title']}")
        print(f"   deadline: {it['deadline_text']!r} -> {it['deadline']}")
        print(f"   event:    {it['event_time_text']!r} -> {it['event_time']}")
        print(f"   eligibility: {it['eligibility']!r} | from msgs {it['source_msgs']}\n")