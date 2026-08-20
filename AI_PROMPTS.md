# AI_PROMPTS.md

This project was built end-to-end in **Claude Code** (an agentic coding CLI
built on Anthropic's Claude models), working directly in this repository —
not by pasting snippets from a chat window. Every prompt below is real,
taken from that session in order; nothing is reconstructed after the fact.

## Tooling

- **AI tool:** Claude Code (Claude Sonnet 5), with direct filesystem access,
  a shell, and an in-app browser used to drive and inspect the running app.
- **Human role:** gave direction, answered clarifying questions, reviewed
  gap analyses the AI produced against the spec, approved scope, and
  supplied the OpenAI API key used in the final LLM integration.

---

## Prompt used for planning

> "Add other packages so that this application can go live."

> "whatever the coding part is remaining implement in this application. If
> any thing remain guide me how to do it."

The AI's planning method throughout was **audit-then-build**, repeated
dozens of times rather than done once up front: read the actual spec
section, re-read the actual current code (never answered from memory),
report a gap table (✅/⚠️/❌), then only build what was missing. The initial
full-project plan came from the instruction provided, which found the app was
frontend-only — no backend, no database, seed data at 320 employees against
a 5,000 minimum — and became the backlog for every subsequent session. Later
planning was feature-scoped, each driven by a spec-section prompt, e.g.:

> "Check these feature if available and if not implement it? 3.1 Employee
> Management" / "3.3 Seat Allocation" / "3.4 New Joiner Allocation" / "3.5
> Search & Filter" / "Check these database requirement is fulfilled or not"
> / "Are these API requirements fulfilled" / "Are these technology
> requirements fulfilled" / "Are these requirements fulfilled: [Core
> Business Rules]"

Each of these was answered by re-testing the live running system (curl,
direct SQLite queries, or driving the browser) before claiming pass/fail —
several turned out to be real gaps despite looking done (see "What AI
generated incorrectly" below).

## Prompt used for database design

> "whatever the coding part is remaining implement in this application..."
> (initial schema)

> "Check these database requirement is fulfilled or not, if not, fulfill
> it: [7. Database Model Suggestion — employees / projects / seats /
> seat_allocations field lists]"

> "Look all these are not mentioned in the database and visible:
> seat_allocations ● id ● employee_id ● seat_id ● project_id ●
> allocation_status ● allocation_date ● released_date"

> "Also add a authentication system for Manager and Employee."

The initial schema (`backend/app/models.py`) followed the spec's suggested
tables almost exactly, plus one deliberate addition: `employee_id`,
`project_id`, and `allocation_date` denormalized directly onto `Seat`
(beyond the spec's minimal list) so the Seat Map can answer "who's in this
seat" in one query instead of joining through `seat_allocations` for every
one of up to 5,600 rows. The verification pass confirmed every spec field
matched exactly. The `seat_allocations` follow-up found the table was
correctly designed and populated but had **zero API exposure** — a real gap
between "the data model is right" and "the requirement is fulfilled" —
fixed by adding relationships to the `SeatAllocation` model, a
`GET /seat-allocations` endpoint, and a History tab. The auth request added
a new `User` table (email, password hash/salt, role, optional
`employee_id` link) — a schema addition the spec doesn't mandate but the
candidate explicitly asked for.

## Prompt used for backend

> "whatever the coding part is remaining implement in this application..."
> (FastAPI app, all REST endpoints, business logic)

> "yes add interactive picker" (after: *"where is system suggesting
> 'available seats'"*)

> "Also add a authentication system for Manager and Employee."

> "This is The Open AI API key, integrate in my application Real LLM
> behind."

The backend (`backend/app/main.py`, `crud.py`) was built as FastAPI + REST
per the spec's recommended stack, with business logic factored out of the
route handlers: duplicate-email/seat rejection, one-seat-per-employee,
reserved/maintenance seats excluded from allocation, project-proximity
preference with alternate-zone fallback. The interactive-picker follow-up
(`GET /seats/suggestions`, an optional `seat_id` on `POST /seats/allocate`
and `POST /employees`) came from the AI itself flagging, unprompted, that
"suggest available seats" had only ever been satisfied by *auto-picking* a
seat — the candidate then asked for the interactive version. Auth added
`security.py` (PBKDF2 password hashing — chosen over bcrypt specifically to
avoid a native-build dependency on Windows) plus `get_current_user` /
`require_manager` FastAPI dependencies gating every existing endpoint. The
LLM integration added `llm_assistant.py` as a new engine tried before the
existing rule-based one, not a replacement of it.

## Prompt used for frontend

> "Make the UI of application Black and purple."

> "whatever the coding part is remaining implement in this application..."
> (rewired the frontend from client-side generation to the new backend API)

> "yes add interactive picker" / "Also add a authentication system..."

The initial ask was pure theming (background/heading color) on an existing
component. The backend build required a much larger frontend change:
`src/api.js` was added as a fetch + snake_case→camelCase normalization
layer, and `src/EtheraSeatDemo.jsx` was rewritten to pull from the API
instead of generating 320 fake employees client-side, with server-side
search/pagination added specifically because search is unusable client-side
once the dataset is 5,000 rows instead of 320. Later prompts added a "New
Joiner" modal, an Edit-employee modal, a seat-picker modal (opened from
both the per-row Allocate button and the New Joiner form), a History tab,
and — for auth — `src/Login.jsx` plus role-based UI gating (Manager sees
every action button; Employee sees "view only" and no History tab, though
the real enforcement is server-side, not just a hidden button).

## Prompt used for AI assistant

> "whatever the coding part is remaining implement in this application..."
> (initial rule-based engine, ported server-side)

> "How many seats are occupied for Project Talos?" (surfaced a real bug,
> see below)

> "which AI is working in this application in the background?"

> "This is The Open AI API key, integrate in my application Real LLM
> behind."

The first version (`ai_assistant.py`) was a keyword/regex parser — the
spec's explicitly-allowed fallback when no AI API is wired up. The
candidate's "Talos" question (an example from the spec's own PDF) exposed
that this fallback had a real control-flow bug, fixed at the time. When
later asked directly which AI was actually running, the honest answer was
"none — it's pattern matching, no LLM call anywhere," which led to the key
being supplied and `llm_assistant.py` being built: OpenAI (`gpt-4o-mini`)
with **function-calling grounded in the real database** (`find_employee_seat`,
`available_seats`, `project_occupancy`, `neighbours`, etc., each backed by
an actual SQL query) so the model looks facts up instead of inventing them,
with the old rule-based parser kept as an automatic fallback on any API
failure.

## Prompt used for debugging

> (implicit, during theming) — a `PowerShell -replace` corrupted non-ASCII
> characters in the file.

> "How many seats are occupied for Project Talos?" → wrong error message.

> "Yeah fix this." (after the AI itself flagged the "are" stopword bug
> found while testing the Talos fix)

> (implicit, during auth/LLM testing) — `uvicorn --reload` hung on Windows
> after a file change; the seat-picker/AI-assistant browser tests kept
> submitting forms with stale values from timing races between synthetic
> `click()`s and React's batched state updates.

Concrete bugs found and fixed, each caught by re-testing rather than
assuming success:
1. **Mojibake** — `PowerShell -replace` read a file with the wrong codepage,
   corrupting `·` and curly quotes into `Â·` etc. Caught by `grep` for the
   corruption pattern, fixed by round-tripping the encoding.
2. **Wrong error message for an unknown project** — asking about
   "Project Talos" (not a real seeded project) fell through the
   occupied-seats branch into an unrelated "employee not found" branch
   instead of saying "no such project." Fixed by scoping that branch's
   trigger condition and adding an explicit not-found message.
3. **"are" swallowed as a name token** — fixing bug #2 surfaced a second
   one: the not-found message extracted "are" instead of "Talos" from
   "How many seats **are** occupied...", because "are" wasn't in the
   parser's stopword list. One-line fix, verified by restarting the server
   and re-running the exact failing query.
4. **`uvicorn --reload` flaky on Windows** — the watcher logged "Reloading…"
   but never finished restarting, so code changes silently didn't take
   effect. Diagnosed via the server log showing no second "Application
   startup complete" line; switched to plain kill-and-restart for every
   backend change from then on.
5. **Browser-automation timing races** — synthetic `.click()` immediately
   followed by `form.requestSubmit()` in the same script sometimes fired
   before React's batched state update committed, submitting stale/empty
   values. Not an app bug, but repeatedly cost debugging time until the
   pattern (fill → separate step → wait → submit) was adopted consistently.
6. **Live-data protection** — mid-session, a database check turned up an
   employee ("Anshu") the AI hadn't created, meaning the running app was
   being used with real data in parallel. The AI flagged this immediately,
   stopped its habitual "reseed to reset to baseline" cleanup step, and
   switched every subsequent test cleanup to targeted `DELETE`/`UPDATE`
   statements that touched only the rows it had just added.

## Prompt used for deployment

> "How to run this using go live in VS code?"

No actual deployment was performed — this remains the one section of the
spec genuinely undone. The AI explained why VS Code's Live Server can't
serve a Vite/JSX project directly (no JSX transform) and gave the two
working local options (`npm run dev`, or build + point Live Server at
`dist/`). Deploying to Railway/Render/Vercel/Netlify, pushing to a GitHub
remote, and provisioning any hosting account were explicitly left to the
candidate — an AI assistant creating accounts or holding deployment
credentials on someone's behalf is out of scope by design, not an
oversight. See `README.md` for the manual steps.

---

## What AI generated correctly

- Every backend endpoint added across the whole session was exercised with
  real `curl` requests (not just read back) before being called done,
  including full round trips: allocate → release → re-allocate on a real
  employee, create → update → deactivate, and — for auth — login as each
  role, an unauthenticated request correctly rejected, an Employee token
  correctly rejected on a manager-only route, and a Manager token
  correctly accepted.
- The LLM integration was checked against cases specifically chosen to be
  hard for a keyword parser: a fully freeform sentence with no fixed
  pattern ("Can you tell me if Priya has a desk yet and which team she's
  on?"), and the exact "Talos" phrasing that had broken the rule-based
  version — the LLM answered both correctly on the first real call.
- `python -m app.seed` output was checked against the spec's minimum-data
  table line by line every time seed logic changed.
- UI changes were driven through the actual browser (DOM text extraction
  and JS-level clicks, since coordinate-based clicks on modals proved
  unreliable mid-session — see debugging log), not just inferred from code:
  Manager login showing all 6 tabs and full row actions, Employee login
  showing 5 tabs with "view only" rows, the seat picker allocating exactly
  the seat clicked (confirmed via a follow-up API call, not just the UI
  echoing back), and the "via OpenAI" engine tag rendering after a real
  LLM answer.
- `npm run build` was re-run after every frontend change to confirm the
  production bundle still compiles cleanly.

## What AI generated incorrectly

- The mojibake encoding bug (see debugging log #1).
- The AI-assistant control-flow bug that produced the wrong error message
  for an unrecognized project name (#2), and the follow-up stopword bug
  in its own fix (#3) — both real logic errors, not just missing features.
- `dashboard_project_utilization`'s SQL query silently dropped
  `Project.description` and `Project.created_at` even though both existed
  correctly on the model and were seeded — the Projects tab simply never
  had the data to show, which looked like a missing UI element but was
  actually two fields lost between the database and the API response.
  Caught because the candidate asked "description is missing" and "date at
  which project created is missing" as two separate prompts; both traced
  to the same underlying pattern in the same query and fixed the same way.
- `seat_allocations` had no API endpoint at all — correct data, invisible
  application. Not a bug exactly, but a genuine gap the AI's own earlier
  "database requirements fulfilled" check had missed by checking the
  schema without checking whether anything actually exposed it.
- `uvicorn --reload`'s Windows flakiness (#4) — not code the AI wrote
  incorrectly, but a tooling assumption (that `--reload` would reliably
  apply changes) that turned out false and had to be worked around.

## What candidate manually fixed

- Nothing in application code — every fix above was made by the AI, not
  the candidate, once identified. The candidate's role was directing which
  spec sections to re-check, asking pointed follow-up questions ("where is
  Project ID created", "which AI is working in the background") that
  forced deeper verification than the AI's own first-pass summaries, and
  supplying the OpenAI API key for the LLM integration.
- The candidate corrected AI's proposed answer format twice: once
  clarifying the intended black/purple scope ("make the background black
  and heading text purple" rather than a full-page recolor), and once
  choosing the Manager/Employee permission model (full edit vs. read-only)
  from a set of options the AI presented rather than the AI assuming one.

## How candidate verified correctness

Every feature-check prompt in this session ("Is X fulfilled, if not fix
it") was itself a verification step initiated by the candidate rather than
trusting the AI's earlier claims — the AI's job on each of those prompts
was to re-derive the answer from the live system (curl, SQLite, or the
browser) and report honestly, including several cases where something
previously marked "done" (search by floor/zone, project description,
project created_at, seat_allocations visibility) turned out to have
regressed or never been fully wired up. The AI was also caught and
corrected mid-session for a process risk of its own making: after
discovering the live "Anshu" record, it stopped auto-reseeding the
database between checks and switched to targeted SQL cleanup, specifically
so the candidate's own real usage of the app wouldn't be silently
destroyed by the AI's habitual "reset to clean baseline" step.
