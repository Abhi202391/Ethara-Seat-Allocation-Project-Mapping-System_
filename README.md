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

## API endpoints

All endpoints from the assessment spec are implemented:

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

`POST /ai/query` implements the assessment's minimum requirement (natural
language "where is X seated" style answers) plus available-seat lookups,
project occupancy, neighbour lookups, and pending-allocation prompts. It's a
keyword/regex-based parser rather than an LLM call — the spec explicitly
allows this fallback when no AI API is wired up ("If the AI API is not
available, candidates can build a fallback keyword-based assistant"). To
upgrade to a real LLM, swap the body of `answer_query()` in
`backend/app/ai_assistant.py` for a call to OpenAI/Claude/Gemini, passing it
the same DB-backed lookups as tools/functions.

## What's implemented vs. not

**Implemented:** full CRUD-backed employee/project/seat management, seat
allocation/release with proximity + alternate-zone fallback, dashboard
aggregation, search/filter (server-side, paginated for 5,000 rows), New
Joiner form with auto-allocation, optional CSV bulk-import, rule-based AI
assistant, Swagger API docs.

**Not implemented (out of scope for this pass):**
- Authentication / role-based access (HR vs. Admin vs. Employee) — the spec
  doesn't strictly require it and none was requested.
- A production Postgres deployment — SQLite is used, which the spec
  explicitly allows for a local/demo deployment. Swapping to Postgres only
  requires changing `DATABASE_URL` in `backend/app/database.py` (SQLAlchemy
  handles the rest).
- Redis caching / LangChain / a real LLM — listed as optional in the spec.

## Deployment

See the deployment guide provided separately — it requires your own
GitHub/Railway/Render/Vercel accounts, which I can't create or authenticate
on your behalf.
