# What Did I Miss?

A local-first AI micro-app that turns overwhelming chat and email threads into a prioritized dashboard of events, assignments, deadlines and tasks. Built for the vibe coding challenge **"The Unread Problem: What Did I Miss?"**.

**Privacy by design:** everything runs on your own laptop. The AI model is local, there are no cloud API calls, and no message ever leaves the device.

## The problem

Students get dozens of messages a day across WhatsApp groups and college email. Important items (hackathon deadlines, assignment submissions, mandatory registrations) get buried under chatter, and people miss them.

## What it does

- Reads WhatsApp chat exports and `.eml` emails
- Filters out chatter ("ok sir", "thanks") and finds items a student needs to act on or attend
- Extracts details: title, category, deadline, event time, venue, eligibility, how to apply, submission format, link
- Resolves deadlines like "by tomorrow", "by next Wednesday" or "15th October 2026" into real dates
- Merges duplicates: the same event posted in several chats or emails becomes one card ("Seen in 3 messages")
- Shows a dashboard with tabs (Tech & Academic, Assessments, Events & Clubs, Notices), urgency badges for items due within 48 hours, and a banner for items due in the next 3 days
- Every card has a **Show original message** button, so you can always verify what the AI extracted

## How it works

```
WhatsApp .txt / .eml files
        |
   Parse and normalize   (ingest.py)
        |
   Prefilter noise, chunk messages   (extract.py)
        |
   Local LLM extraction to structured JSON   (Ollama, Qwen2.5 7B)
        |
   Resolve dates in code, not by the model   (dateparser + custom rules)
        |
   Store and merge duplicates   (SQLite + rapidfuzz, db.py)
        |
   Dashboard   (FastAPI + one HTML page)
```

A key design choice: small local models are unreliable at date arithmetic, so the model only copies the deadline text. Code converts it to a real date, using the message's own timestamp as the reference for words like "tomorrow".

## Tech stack

| Part | Tool |
|---|---|
| Local LLM | Ollama with `qwen2.5:7b-instruct` |
| Backend | Python, FastAPI, Uvicorn |
| Storage | SQLite |
| Dates | dateparser plus custom weekday handling |
| Dedupe | rapidfuzz |
| Frontend | One HTML file, vanilla JS |

## Setup (Windows, PowerShell)

**Requirements:** Python 3.10 or newer, [Ollama](https://ollama.com/download), and a GPU with about 8 GB VRAM (it also runs on CPU, more slowly).

```powershell
# 1. Get the model
ollama pull qwen2.5:7b-instruct

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

## Run it

Process the sample data (all fake), then start the dashboard:

```powershell
python pipeline.py data\college_cse_group.txt
python pipeline.py data\club_announcements.txt
python pipeline.py data\emails

uvicorn main:app --reload
```

Open **http://localhost:8000**.

- `pipeline.py` accepts a WhatsApp `.txt` file, a single `.eml` file, or a folder of `.eml` files.
- For chats that have no date in each line, pass a default date: `python pipeline.py data\chat.txt 2026-10-09`.
- Messages are cached by hash, so running the pipeline twice never reprocesses or duplicates anything.
- To start fresh, stop the server and delete `data\unread.db`.

## Project structure

```
ingest.py      parsers for WhatsApp exports and .eml emails
extract.py     prefilter, LLM extraction, date resolution
db.py          SQLite storage and duplicate merging
pipeline.py    runs ingest, extract and store end to end
main.py        FastAPI server and API
static/        dashboard (index.html)
data/          fake sample chats and emails
prompt.md      log of the prompts used to build this project
```

## Sample data

All data in `data/` is fake: invented names, example links and placeholder numbers. It includes a hackathon posted in a chat and in an email (to test dedupe), faculty assignments, a club inauguration, workshops with eligibility rules, relative deadlines and plenty of noise.

## Limitations

- **WhatsApp has no official personal-account API.** The app reads the "Export chat" `.txt` file, so import is manual.
- **Attachments are not read.** PDFs and images appear only as file names.
- **A 7B model is imperfect.** It sometimes mislabels a category or merges two separate actions into one item. The original-message button exists for this reason.
- **"Next Wednesday" is ambiguous.** The app picks the first matching weekday after the message date.
- **Email import is file-based.** There is no live Gmail sync yet.

## Roadmap

- Automatic Gmail sync via IMAP
- Reading PDF and image attachments locally
- Desktop notifications for approaching deadlines
- A paste box for classifying a single new message live
- A "mark as done" state on cards

## Built with AI assistance

This project was built in one session with Claude as a coding and architecture assistant. The full prompt history is in [`prompt.md`](prompt.md).

## Author

Your Name, your college, your year
