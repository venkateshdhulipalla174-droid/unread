# Prompt Log: "The Unread Problem: What Did I Miss?"

**Challenge:** Vibe coding challenge, build a simple local-first AI micro-app that summarizes and prioritizes overwhelming chat conversations.
**AI assistant used:** Claude (chat), one continuous conversation on 9 Oct 2026.
**Result:** A working local prototype: WhatsApp and email ingestion, local LLM extraction, deadline resolution, dedupe, and a dashboard.

Prompts are quoted exactly as I typed them. Where I pasted terminal output or screenshots, I describe them in [brackets].

---

## Phase 1: Defining the problem and architecture

**Prompt 1 (problem + my plan)**
> This is the problem statement I got in a vibe coding challenge. I need your assistance to develop a solution and prototype for this. My plan: the AI model should analyse different messages across whatsapp and gmail (official college id and personal). Then it should be able to categorise into different categories like: Academic or technical events (sub categories: domains of the event, eligibility, application process etc and deadline should be highlighted), non-technical events, assessment works, inaugrations of any clubs etc. The app should have a simple interface that shows these categories highlighting all important details for tech events or academic opportunities, then assessment works given by faculty with deadlines, submission format etc. Then non-tech events or any other events happening in college. The micro app should run locally in order to maintain privacy. It should solve the problem of students who waste a lot of time seeing all the messages and someone who misses some important events. So act as a systems architect and suggest me how we can make a simple working system that can be made in 3 hours, by defining the system design and overall architecture

[Attached: photo of the challenge slide]

**Outcome:** Architecture of ingest, normalize, prefilter, local LLM extract, store, dashboard, plus a 3-hour plan. The AI also challenged two assumptions in my plan: WhatsApp has no official personal API (so use chat export), and small local models are bad at relative dates (so resolve dates in code).

## Phase 2: Hardware check and breakdown

**Prompt 2**
> I am building on my laptop having 24gb vram

**Prompt 3**
> Let's breakdown the project into chunks: tell me what should I do first and where I should do with clear steps

**Prompt 4**
> [Pasted `nvidia-smi` output, which showed an RTX 5050 with 8 GB VRAM]

**Outcome:** My "24 GB" claim was wrong (it was probably system RAM). The plan switched from a 14B model to a 7B model (`qwen2.5:7b-instruct`) with smaller chunks and a stricter prefilter.

**Prompt 5**
> Also clearly explain me about all the chunks that you have divided , like what does each chunk build

**Outcome:** Seven chunks defined: setup, sample data, parsers, extraction, storage and dedupe, UI, demo polish.

## Phase 3: Chunk 0, setup

**Prompt 6**
> now, let's do chunk 0 step by step. Guide me clearly, where to run code, where to install, and what folders and files I have to create

**Follow-ups (short):** "ollama version is 0.40.2"; [pasted `ollama ps`] "it is 100% GPU"; "python version is 3.14.8"; [pasted venv activation and execution-policy fix]; [screenshots of `ni` file creation and `dir`]; [screenshot of `pip list`]; "python test_ollama.py local model working"

**Outcome:** Ollama running Qwen2.5 7B at 100% GPU, Python 3.14 virtual environment, libraries installed, project folder created, Python-to-model test passing.

## Phase 4: Chunk 1, sample data (and a privacy decision)

**Prompts**
> Shall I paste the real messages?

> We don't need to mention real names right, I will upload the chat changing names or any personal details

> where to create data file

> I didn't get what you are trying to say

**Outcome:** I decided to use fake data only, both for testing and for the demo, because the app's whole point is that chats never leave the device. I later asked the same question about real emails and chose fake data again:

> shall I paste real emails

> leave it, we will use fake data

**Prompt (sample chat format)**
> convert the message into the preferred format , I don't have time

[I had pasted an excerpt of a real group chat. It was converted into a fake-name version with a standard timestamp format and an answer key, `expected.md`.]

## Phase 5: Chunk 2, parser

**Prompts**
> yes, it is saved

> it showed me parsed 0 messages

[Pasted the 0-message output, a `dir data` screenshot showing a 711-byte file, and a screenshot showing the answer key had been saved into the chat file by mistake.]

> yeah it parsed 15 messages

**Outcome:** Parser handling multi-line messages, forwarded tags and quoted replies. The 0-message bug came from the wrong content in the file, not from the code.

## Phase 6: Chunk 3, LLM extraction

**Prompt**
> I don't have time to write myself

[Pasted extractor output four times, after each prompt revision.]

**Outcome (iterations):**
1. First run: wrong categories, and an invented "Open to all" eligibility.
2. Added category definitions and a rule to leave eligibility empty if unstated. The model copied my example text into the wrong item, so I removed the example.
3. Date bugs: the model returned ISO dates that were read as day/month swapped, and it copied whole sentences into the deadline field. Fixed in code (ISO handling, searching for a date inside a sentence, a fallback scan for "by / before / due" phrases).
4. All dates correct: project 10 Oct, survey 15 Oct, event 11 Oct 06:00.

## Phase 7: Chunk 4 and 5, storage, dedupe, UI

**Prompts**
> yes, in the first run, I got 15 messages and in run2 0 messages with the same 4 items

> I don't have any content in main.py

> tell me where exactly I need to do changes in db.py

[Pasted the uvicorn startup screenshot, then dashboard screenshots before and after two fixes: sort order and date formatting.]

> damn!, it worked

**Outcome:** SQLite storage, fuzzy dedupe (one card for a message seen in several places, with a count), a message-hash cache so reruns skip processed messages, and a dashboard with tabs, urgency badges, a 3-day banner, and a "Show original message" button.

## Phase 8: Second source, more data, debugging

**Prompts**
> how to stop uvicorn

> I think I clicked ctrl+c here by mistake, this new terminal where we created emails stopped working

[Pasted screenshots of: an empty dashboard after a rebuild, a pipeline traceback (`UnboundLocalError` in the date resolver), and the final working state.]

> it worked!, I am able to see everything

**Outcome:** Added a club chat (hackathon, workshop, inauguration, internship) and fake `.eml` emails through the same pipeline. Added a weekday resolver for phrases like "by next Wednesday" and "by Sunday". The traceback was fixed by replacing the whole `resolve` function.

---

## What I learned about prompting

- **Giving the AI my own plan first got better answers.** It critiqued my plan instead of starting from scratch.
- **Real data (my hardware, my files) corrected the AI's assumptions.** My GPU output showed the 24 GB figure was wrong.
- **Pasting exact errors and screenshots solved bugs quickly.** Each bug took one round trip.
- **Small local models drift when the prompt changes.** Examples inside a prompt can leak into answers, so critical logic (dates, dedupe) went into code instead.
- **I tested on fake data and checked results against an answer key** instead of trusting the model's output.

## Known limits (stated honestly)

- WhatsApp needs a manual chat export (no official personal-account API).
- Attachments (PDFs, images) are not read.
- A 7B model sometimes mislabels categories or merges two separate actions into one item.
- "Next <weekday>" is ambiguous even for people; the app picks the first matching day after the message date.
- The "Show original message" button is the safety net for all of these.