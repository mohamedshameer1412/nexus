# StudyHub — Phase B report: multiple-choice questions from uploaded material

Scope: **only** MCQ generation from a subject's uploaded material (per your instruction). **Not in this phase:** taking a quiz, scoring,
progress, weak-topic detection, the backward pass, spaced repetition.

## What exists

| Piece | File |
|---|---|
| Generate → check in code → independent solver → revise → store; shuffling; the checks | `studyhub/mcq.py` |
| Question bank and job tables (migration 5); scoped queries | `studyhub/db.py`, `studyhub/repo.py` |
| Generate form, background job page, question bank, show-answer-and-source | `studyhub/web/app.py`, `studyhub/web/ui.py` |
| Terminal command | `scripts/studyhub_mcq.py` |
| Step log in plain words (shared with the web page) | `studyhub/explain.py` |

Use it: subject page → **Multiple-choice questions** → pick a topic or the whole subject, 1 to 10 questions → **Generate questions**.
Terminal: `python scripts/studyhub_mcq.py --demo --count 3` or `--user NAME --subject "Subject" --count 5 [--topic TEXT] [--save]`.

## How a question is made and kept

1. **Passages** of a topic (three consecutive ones, at a random start, so repeat runs cover different parts). Passages that read like
   instructions to an AI are never used.
2. **Draft**: the local model (Ollama first; the cloud model only under the same key + consent + allow-list + daily-cap rules as the answers)
   returns the correct answer, three wrong answers, an exact quote, a one-line explanation. It never chooses where the answer goes.
3. **Checked in code**: the quote is word for word in the material; the question does not contain its answer; four distinct options of
   similar length; no "all of the above", no letter labels; no invented numbers; the answer is stated by the quote; the question is not a
   repeat of one already in the bank; **no wrong answer is a copy of any sentence of the passage** (it would be a true statement).
4. **Independent reader**: a second call answers each surviving question from the passages without seeing the key. If it picks a different
   option (or none), the question is sent back with that reason, at most twice.
5. **Stored**: the app shuffles the options (reproducibly) and records where the answer is. Each question keeps its source (file, section,
   PDF page) and exact words, and whether the independent reader confirmed it.
6. **If no model is available, nothing is written**, and the page says so. A batch that cannot deliver says how many passed ("1 of 3").

## Evidence

**Automated:** 757 passed, 4 skipped, 0 failed in the project (`test_studyhub_mcq`, `test_studyhub_mcq_web`: the rules, shuffling, solver,
revision bounds, storage, ownership, XSS, CSRF, the background worker, cloud-guard reuse). Each safeguard was switched off in turn and a
test failed every time (quote check, solver gate, answer leak, restatement, identical options, duplicate questions, three-distractor
rule, number rule, answer-stated-by-quote, shuffle, quarantine, and three ownership checks).

**Real local model (llama3.1 8B), sample material:** 3 of 3 questions kept, 0 rejected, all confirmed by the independent reader; the
answers landed on B, C and D.

**Real local model, a real 326-page textbook and a 3-page syllabus from your own "Signals" subject** (read from your database, nothing
saved; the output is not committed because it quotes a copyrighted book). Two runs taught the most:
- Run with the strict rule: 1 of 3 kept, 6 candidates rejected. The syllabus questions were rejected because their wrong answers were
  other real items from the same list.
- I then relaxed that rule (leaving it to the independent reader) and got 4 of 4 kept. **Reading the questions showed two were wrong.**
  "What is one of the lab experiments?" had four real lab experiments as its options, so all four were correct, and the 8B reader agreed
  with the key. Another had an option that was the first half of the right answer. The strict rule had been right. It is restored, with a
  regression test built from that case.

**Real browser** (Edge, real server, real local model, real upload): **17 of 17 checks passed** ([log and screenshots](studyhub-evidence/b/)): the job page refreshes by itself and then shows 3 questions; each has 4 different options; the answer is hidden until "Show answer and source" is opened; the revealed letter is the option holding the answer; every quote is confirmed against the uploaded file by the test itself; the answer letters were B, C and D (shuffled by the app); topic filter, delete, a refused count, another account getting 404, and 0 JavaScript errors. (A first run showed 15/17 because my test scraped the answer text badly; the test was fixed, not the app, and repeated.)

## Known limits — read before relying on this

- **A small local reader does not reliably notice a question with several correct options.** The code rule above catches the common case
  (wrong answers copied from the source). It does not catch wrong answers that are true in the source but worded differently.
  Read the questions before using them for anything that matters. A stronger second model (the cloud fallback) is not tested.
- **The final (strict) rule was not re-run on your textbook.** Its effect there is known only from the first run (1 of 3 kept) and the unit tests; expect few or no questions from list-like documents such as a syllabus.
- **Fewer questions than asked is normal** on list-like or short material. Every rejection is in the step log.
- **Questions are mostly recall of one stated fact**, some are plain ("What type of collection is a stack?"), and a few are awkwardly
  worded (one on the textbook said "interface class"). No difficulty levels, no coverage guarantee across the whole subject.
- **Text extracted from PDFs can be messy** (stray spaces in quotes, code fragments); quotes are the material's own text, so they show that.
- A subject without an outline is one big topic; questions then come from random three-passage windows of it.
- **Time:** about 10 to 45 s per batch locally, plus the reader; 3 to 4 minutes for a 4-question job on the textbook. Jobs run one at a time.
- The cloud path is still untested live (no key). Only Edge was used for the browser test.
