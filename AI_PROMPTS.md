# AI_PROMPTS.md

This project was built end-to-end in **Claude Code** (an agentic coding CLI
built on Anthropic's Claude models), working directly in this repository —
not by pasting snippets from a chat window. This file documents the actual
prompts given during that session, what the AI produced, what was wrong,
and how each change was verified before moving on.

## Tooling

- **AI tool:** Claude Code (Claude Sonnet 5), with direct filesystem access,
  a shell, and an in-app browser used to drive and inspect the running app.
- **Human role:** gave direction, answered clarifying questions, reviewed
  gap analysis, approved scope.

## Prompt log (chronological, verbatim intent)

### 1. Planning / UI theming
> "Make the UI of application Black and purple."

The AI found two near-duplicate component files in the project
(`EtheraSeatDemo.jsx`, `EtheraSeatDemo_1.jsx`) with different color themes
and no build config to indicate which was "live". Rather than guess, it
asked which file to target and, once told the black/purple file needed
refinement, asked a second clarifying question about scope (deepen all
accents vs. touch only background/heading). The human answered: "Make the
background black and Heading text purple color."

**What AI generated incorrectly:** a `PowerShell -replace` command used to
bulk-swap a background color (`#0A0710` → `#000000`) read the file with
PowerShell's default codepage instead of UTF-8, corrupting every non-ASCII
character in the file (the `·` separator, curly quotes) into mojibake
(`Â·` etc.).

**How it was caught and fixed:** a follow-up `grep` for the mojibake byte
pattern (`Â|â€`) found 12 corrupted occurrences. Fixed by round-tripping the
string through the CP1252→UTF-8 encoding pair that caused the corruption
(read as UTF-8, re-encode as CP1252 bytes, decode those bytes as UTF-8),
then re-verified with the same grep (0 matches) and a direct file read.

### 2. Packaging for deployment
> "Add other packages so that this application can go live."

The AI scaffolded a full Vite + React + Tailwind project around the
existing component (`package.json`, `vite.config.js`, `tailwind.config.js`,
`postcss.config.js`, `index.html`, `src/main.jsx`), moved the component into
`src/`, ran `npm install`, then verified with `npm run build` (production
bundle) and `npm run dev` (served via the in-app browser, checked page text
and console for errors) before reporting done.

### 3. Clarifying question (no code)
> "How to run this using go live in VS code?"

Explained why VS Code's Live Server extension can't run a Vite/JSX project
directly (it doesn't transpile JSX) and gave the two working options:
`npm run dev`, or building first and pointing Live Server at `dist/`.

### 4. Requirements gap analysis
> Uploaded `Vibe Coding Assessment_ Ethara Seat Allocation & Project Mapping
> System.pdf`, then: "CHECK from this document."

The AI read the full assessment PDF and produced a section-by-section
comparison against the actual codebase (not from memory — it re-read the
current component file first), splitting findings into Implemented /
Partial / Missing. This surfaced that the app was frontend-only with no
backend, no database, and seed data far below the spec's minimums (320
employees vs. 5,000 required).

### 5. Backend implementation
> "whatever the coding part is remaining implement in this application. If
> any thing remain guide me how to do it."

Given the gap analysis from step 4, the AI built the missing backend:

- **Database design:** SQLAlchemy models for `Employee`, `Project`, `Seat`,
  `SeatAllocation` (`backend/app/models.py`), following the assessment's
  suggested schema, plus a `(floor, zone, seat_number)` unique constraint to
  enforce business rule #7 (no duplicate seat numbers per floor/zone) at
  the database level rather than only in application code.
- **Backend APIs:** every endpoint listed in the assessment's API section
  (`backend/app/main.py`), with business logic factored into
  `backend/app/crud.py` — duplicate-email rejection, one-seat-per-employee
  enforcement, reserved/maintenance seats excluded from allocation,
  project-proximity seat preference with alternate-zone fallback.
- **AI assistant:** ported the rule-based query parser to run server-side
  against the real database (`backend/app/ai_assistant.py`), exposed as
  `POST /ai/query` per the spec's exact request/response shape.
- **Seed data:** `backend/app/seed.py`, sized to clear every minimum in the
  spec's "Sample Data Requirement" table (5,000 employees, 5,600 seats
  across 10 zones, 168 reserved, 528 available, 180 pending).
- **Frontend rewiring:** `src/api.js` (fetch layer + snake_case→camelCase
  normalization) and a rewritten `src/EtheraSeatDemo.jsx` that fetches from
  the backend instead of generating data client-side, with server-side
  search/pagination (needed once the dataset is 5,000 rows instead of 320),
  a debounced search box, a "New Joiner" modal (`POST /employees` with
  auto-allocation), and an optional CSV bulk-import button.

### 6. Debugging encountered during backend build

- SQLAlchemy 2.0's `case()` requires positional `(condition, value)` tuples
  rather than the 1.x keyword form — written correctly on the first pass
  after checking the installed SQLAlchemy version (2.0.52).
- `pip` was missing from the system Python install; bootstrapped with
  `python -m ensurepip --upgrade` before installing backend dependencies.
- No other runtime errors surfaced during backend testing — endpoints
  worked on the first `curl` pass.

## What AI generated correctly (verified, not assumed)

- Every backend endpoint was exercised with real `curl` requests and
  inspected JSON responses before being considered done: `GET /health`,
  `GET /dashboard/summary`, `GET /employees?search=amit`, `POST /ai/query`,
  and a full `allocate → release → re-allocate` round trip on a specific
  pending employee to confirm state transitions matched the business rules.
- `python -m app.seed` output was checked against the spec's minimum-data
  table line by line (5,000/5,600/10 zones/168 reserved/528
  available/180 pending — all pass).
- The full stack was driven through the actual UI in the browser (not just
  curl): clicked through all five tabs, typed into the employee search box
  and confirmed server-side filtering worked, submitted an AI Assistant
  question and confirmed the answer came from the live database (occupied
  count for project Indigo matched the dashboard), opened the "Add
  Employee" modal and created a real record, and confirmed the header's
  live employee count incremented afterward. Console and network logs were
  checked for errors at each step.
- `npm run build` was re-run after the rewrite to confirm the production
  bundle still compiles cleanly.
- After testing, the database was re-seeded to reset it to the pristine,
  documented baseline numbers rather than leaving test-mutated counts in
  place.

## What was manually fixed (not AI-generated correctly on the first try)

- The mojibake encoding bug from step 1, described above.
- Two scope-clarifying questions were asked instead of guessing (which
  file to theme; how far "make it purple" should extend) — this isn't a
  code fix, but it's the mechanism that kept the AI from redoing work on
  the wrong target.

## What's still open

Deployment (Railway/Render/Vercel/Netlify), pushing to a GitHub remote, and
authentication were **not** done by the AI — they require the candidate's
own accounts and credentials, which an AI assistant should not create or
hold. See `README.md`'s deployment section for the manual steps.
