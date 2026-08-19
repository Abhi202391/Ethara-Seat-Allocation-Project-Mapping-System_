"""Rule-based natural-language query assistant.

Mirrors the frontend's fallback assistant but runs server-side against the
real database, per the assessment's POST /ai/query requirement. If no AI API
key is configured this remains the answering engine (spec explicitly allows
a keyword-based fallback when no AI API is available).
"""

import re
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models

STOPWORDS = {
    "where", "is", "seated", "seat", "who", "sitting", "near", "me", "which",
    "project", "assigned", "to", "for", "how", "many", "seats", "occupied",
    "available", "on", "floor", "the", "a", "an", "of", "allocate", "new",
    "employee", "joining", "today", "show", "all", "what", "am", "i",
}


def _extract_name_token(raw_query: str) -> Optional[str]:
    words = re.findall(r"[A-Za-z]+", raw_query)
    candidates = [w for w in words if w.lower() not in STOPWORDS]
    return candidates[0] if candidates else None


def _find_employee_by_first_name(db: Session, token: str) -> Optional[models.Employee]:
    like = f"{token.lower()}%"
    return db.query(models.Employee).filter(func.lower(models.Employee.name).like(like)).first()


def answer_query(db: Session, raw_query: str) -> str:
    q = raw_query.lower().strip()

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", q)
    if email_match:
        email = email_match.group(0)
        emp = db.query(models.Employee).filter(func.lower(models.Employee.email) == email).first()
        if not emp:
            return f"I couldn't find an employee with email {email}."
        proj = emp.project.name if emp.project else "no project"
        if not emp.seat:
            return f"{emp.name} has not been allocated a seat yet. They're assigned to project {proj}."
        seat = emp.seat
        return (
            f"You are allocated Floor {seat.floor}, Zone {seat.zone}, Bay {seat.bay}, "
            f"Seat {seat.seat_number}. Your project is {proj}."
        )

    floor_avail_match = re.search(r"floor\s*(\d+)", q)
    if floor_avail_match and any(w in q for w in ("available", "free", "empty")):
        floor = int(floor_avail_match.group(1))
        seats = (
            db.query(models.Seat)
            .filter(models.Seat.floor == floor, models.Seat.status == "Available")
            .limit(500)
            .all()
        )
        if not seats:
            return f"There are no available seats on Floor {floor} right now."
        total = db.query(func.count(models.Seat.id)).filter(
            models.Seat.floor == floor, models.Seat.status == "Available"
        ).scalar()
        sample = ", ".join(s.seat_number for s in seats[:6])
        suffix = "…" if total > 6 else ""
        plural = "" if total == 1 else "s"
        return f"Floor {floor} has {total} available seat{plural}, including: {sample}{suffix}."

    if "project" in q and any(w in q for w in ("occupied", "how many", "utilization", "seats for")):
        projects = db.query(models.Project).all()
        proj = next((p for p in projects if p.name.lower() in q), None)
        if proj:
            occ = db.query(func.count(models.Seat.id)).filter(
                models.Seat.project_id == proj.id, models.Seat.status == "Occupied"
            ).scalar()
            emp_count = db.query(func.count(models.Employee.id)).filter(
                models.Employee.project_id == proj.id
            ).scalar()
            occ_plural = "" if occ == 1 else "s"
            emp_plural = "" if emp_count == 1 else "s"
            return (
                f"Project {proj.name} has {occ} occupied seat{occ_plural} across "
                f"{emp_count} assigned employee{emp_plural}."
            )
        token = _extract_name_token(raw_query)
        available_names = ", ".join(p.name for p in projects)
        return (
            f"I couldn't find a project called {token or 'that'}. "
            f"Available projects: {available_names}."
        )

    if any(p in q for p in ("who is sitting near", "near me", "neighbours", "neighbors")):
        token = _extract_name_token(raw_query)
        emp = _find_employee_by_first_name(db, token) if token else None
        if not emp or not emp.seat:
            return "I need a valid, seated employee name to find their neighbours — try “who is sitting near Amit”."
        seat = emp.seat
        neighbours = (
            db.query(models.Employee)
            .join(models.Seat, models.Seat.employee_id == models.Employee.id)
            .filter(
                models.Seat.floor == seat.floor,
                models.Seat.zone == seat.zone,
                models.Seat.bay == seat.bay,
                models.Employee.id != emp.id,
            )
            .limit(20)
            .all()
        )
        if not neighbours:
            return f"{emp.name} is in Bay {seat.bay}, Zone {seat.zone}, Floor {seat.floor} — no other allocated neighbours in that bay right now."
        names = ", ".join(n.name for n in neighbours)
        return f"{emp.name} sits in Bay {seat.bay}, Zone {seat.zone}, Floor {seat.floor}, near: {names}."

    if "project" in q and any(p in q for p in ("assigned", "which project", "what project")):
        token = _extract_name_token(raw_query)
        emp = _find_employee_by_first_name(db, token) if token else None
        if not emp:
            return "Tell me the employee's name to look up their project, e.g. “which project is Priya assigned to?”"
        proj = emp.project.name if emp.project else "no project"
        return f"{emp.name} is assigned to project {proj}."

    if "where is" in q or "seat" in q:
        token = _extract_name_token(raw_query)
        emp = _find_employee_by_first_name(db, token) if token else None
        if not emp:
            return "I couldn't find that employee. Try their first name, e.g. “where is Amit seated?”"
        proj = emp.project.name if emp.project else "no project"
        if not emp.seat:
            return f"{emp.name} has not been allocated a seat yet. They're assigned to project {proj}."
        seat = emp.seat
        return (
            f"{emp.name} is seated on Floor {seat.floor}, Zone {seat.zone}, Bay {seat.bay}, "
            f"Seat {seat.seat_number}. They are assigned to Project {proj}."
        )

    if "allocate" in q and "new" in q:
        pending = (
            db.query(models.Employee)
            .outerjoin(models.Seat, models.Seat.employee_id == models.Employee.id)
            .filter(models.Seat.id.is_(None))
            .first()
        )
        if not pending:
            return "There are no pending new joiners awaiting seat allocation right now."
        return (
            f"{pending.name} ({pending.employee_code}) is pending allocation. "
            f"Open the Employees tab and click “Allocate” to assign the next available seat."
        )

    return (
        "I couldn't quite parse that. Try: “where is Amit seated”, “available seats on floor 3”, "
        "“how many seats occupied for project Indigo”, or “who is sitting near Priya”."
    )
