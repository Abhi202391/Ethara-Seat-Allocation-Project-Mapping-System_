# Ethara Seat Allocation & Project Mapping System

A full-stack app for tracking employee seating, project assignment, floor/zone
occupancy, and new-joiner allocation across Ethara's offices, built for the
"Vibe Coding Assessment: Ethara Seat Allocation & Project Mapping System".

## Architecture

```
Ethara/
├── src/                  React frontend (Vite + Tailwind CSS)
│   ├── EtheraSeatDemo.jsx   Main UI: dashboard, employees, seat map, projects, AI chat
│   ├── api.js               Fetch wrapper + snake_case→camelCase normalization
│   └── main.jsx
├── backend/               FastAPI backend
│   └── app/
│       ├── main.py          All REST endpoints
│       ├── models.py        SQLAlchemy models (Employee, Project, Seat, SeatAllocation)
│       ├── schemas.py        Pydantic request/response schemas
│       ├── crud.py           Business logic: allocation rules, dashboard aggregation
│       ├── ai_assistant.py   Rule-based NL query engine (POST /ai/query)
│       ├── seed.py           Deterministic seed data generator
│       └── database.py       SQLite engine/session
├── package.json
└── vite.config.js
```

**Stack:** React 18 + Tailwind CSS (frontend) · FastAPI + SQLAlchemy + SQLite
(backend) — matches the assessment's recommended stack (SQLite is explicitly
listed as acceptable for a local demo).

## Why a backend was added

The original build was a frontend-only mock (data generated in-browser,
reset on every reload). This didn't meet the assessment's core requirement of
a "full-stack application" with a real database, REST API, and durable seat
state — an allocation had to survive a page refresh and be visible to a
second browser tab. The FastAPI + SQLite backend below replaces that
in-memory generator with real persistence and enforces the business rules
server-side instead of only in the UI.

## Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # optional — add OPENAI_API_KEY here for the real LLM assistant
python -m app.seed            # creates ethara.db and seeds it (run once, or to reset)
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger UI): http://localhost:8000/docs

### Frontend

```bash
npm install
npm run dev
```

App: http://localhost:5173

By default the frontend talks to `http://localhost:8000`. To point it at a
different backend, copy `.env.example` to `.env` and set `VITE_API_URL`.

## Seed data

`python -m app.seed` generates deterministic data meeting the assessment's
minimums:

| Requirement | Minimum | Generated |
|---|---|---|
| Employees | 5,000 | 5,000 |
| Floors | 5 | 5 |
| Zones | 10 | 10 (5 floors × 2 zones) |
| Seats | 5,500 | 5,600 |
| Projects | 10 | 11 |
| Available seats | 500 | 528 |
| Reserved seats | 100 | 168 |
| Pending employees | 50 | 180 |

Re-running the script drops and recreates all tables (useful to reset to a
clean demo state).

## Authentication

Two roles: **Manager** (full access — add/edit/deactivate employees,
allocate/release seats, import CSV, view the audit History tab) and
**Employee** (read-only — can browse and search the entire directory, but
no action buttons; the backend rejects mutating requests from an Employee
token with `403` regardless of what the UI shows).

Demo accounts (seeded by `python -m app.seed`, or click the quick-fill
buttons on the login screen):

| Role | Email | Password |
|---|---|---|
| Manager | `manager@ethara.ai` | `Manager@123` |
| Employee | `employee@ethara.ai` | `Employee@123` (linked to the first seeded employee) |

Auth is a bearer JWT (`POST /auth/login`, 12h expiry), password hashing is
PBKDF2-SHA256 via the stdlib (`backend/app/security.py` — chosen over
bcrypt to avoid a native-build dependency on Windows).

## API endpoints

All endpoints from the assessment spec are implemented (all require a
valid bearer token; mutating routes additionally require `role=manager`):

**Auth:** `POST /auth/login` · `GET /auth/me`

**Employees:** `POST /employees` · `GET /employees` (search, status, page,
page_size) · `GET /employees/{id}` · `PUT /employees/{id}` · `DELETE
/employees/{id}` (deactivates + releases seat) · `POST
/employees/import-csv` (bulk add via CSV, optional feature)

**Projects:** `POST /projects` · `GET /projects` · `GET
/projects/{id}/employees`

**Seats:** `POST /seats` · `GET /seats` (floor, zone, status filters) · `GET
/seats/available` · `POST /seats/allocate` · `POST /seats/release`

**Dashboard:** `GET /dashboard/summary` · `GET
/dashboard/project-utilization` · `GET /dashboard/floor-utilization`

**AI Assistant:** `POST /ai/query` — rule-based natural-language answering
(no external AI API key required; see "AI Assistant" below)

Full request/response schemas: http://localhost:8000/docs

## Business rules enforced (server-side)

1. One employee can have only one active seat — `allocate_seat` rejects if
   the employee already has a seat.
2. One seat can be allocated to only one active employee — allocation only
   pulls from seats with `status = Available`.
3. Released seats become available again — `release_seat` resets status,
   clears employee/project/date.
4. Reserved/Maintenance seats are never offered by the allocator.
5. New joiners are seated near their project teammates when possible: the
   allocator first looks for the floor where their project already has the
   most occupied seats, then falls back to any available seat (surfaced to
   the caller as a `note` in the allocate response).
6. Duplicate employee email is rejected (`400`).
7. Duplicate seat number on the same floor/zone is rejected via a DB unique
   constraint (`floor, zone, seat_number`).
8. Dashboard numbers are computed live from the database on every request —
   they always reflect the latest allocation/release.

## AI Assistant

`POST /ai/query` answers natural-language questions about seats, projects,
and allocation status. Two engines:

- **LLM (real AI)** — when `OPENAI_API_KEY` is set (`backend/.env`, see
  `backend/.env.example`), `backend/app/llm_assistant.py` calls OpenAI
  (`gpt-4o-mini` by default, override via `OPENAI_MODEL`) using
  function-calling: the model is given tools like `find_employee_seat`,
  `available_seats`, `project_occupancy`, and `neighbours`, each backed by a
  real database query. This grounds every answer in actual data — the model
  can't hallucinate a seat number — while understanding phrasing far more
  flexibly than a fixed parser (e.g. "Can you tell me if Priya has a desk
  yet and which team she's on?" with no fixed pattern to match).
- **Rule-based fallback** — `backend/app/ai_assistant.py`, a keyword/regex
  parser. Used automatically whenever no API key is configured, or if the
  OpenAI call itself fails for any reason (network, auth, rate limit) — the
  request never errors out, it just answers with the simpler engine. This is
  also what the spec explicitly allows when no AI API is available ("If the
  AI API is not available, candidates can build a fallback keyword-based
  assistant").

Every `/ai/query` response includes `"engine": "llm" | "rule-based"` so the
frontend (and you) can see which one actually answered — the AI Assistant
tab shows a small "via OpenAI" / "via rule-based fallback" tag under each
answer.

## What's implemented vs. not

**Implemented:** full CRUD-backed employee/project/seat management, seat
allocation/release with proximity + alternate-zone fallback, interactive
seat picker, dashboard aggregation, search/filter (server-side, paginated
for 5,000 rows), New Joiner form with auto-allocation, optional CSV
bulk-import, rule-based AI assistant, seat_allocations audit trail with a
History tab, Manager/Employee authentication with role-based access
control, Swagger API docs.

**Not implemented (out of scope for this pass):**
- A production Postgres deployment — SQLite is used, which the spec
  explicitly allows for a local/demo deployment. Swapping to Postgres only
  requires changing `DATABASE_URL` in `backend/app/database.py` (SQLAlchemy
  handles the rest).
- Redis caching / LangChain / a real LLM — listed as optional in the spec.

## Deployment

See the deployment guide provided separately — it requires your own
GitHub/Railway/Render/Vercel accounts, which I can't create or authenticate
on your behalf.
