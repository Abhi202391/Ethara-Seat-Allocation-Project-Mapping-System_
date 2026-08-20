"""Real LLM-backed assistant (OpenAI), grounded via function-calling against
the live database so it answers from real records instead of guessing.

Falls back to the rule-based assistant (ai_assistant.py) automatically if
no API key is configured, or if the API call itself fails for any reason
(network, auth, rate limit) -- see main.py's /ai/query handler.
"""

import json
import os
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def is_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


# ---------------- tool implementations (grounded in the real DB) ----------------

def _find_employee(db: Session, name_or_email: str) -> Optional[models.Employee]:
    q = name_or_email.strip().lower()
    emp = db.query(models.Employee).filter(func.lower(models.Employee.email) == q).first()
    if emp:
        return emp
    return db.query(models.Employee).filter(func.lower(models.Employee.name).like(f"{q}%")).first()


def tool_find_employee_seat(db: Session, name_or_email: str) -> dict:
    emp = _find_employee(db, name_or_email)
    if not emp:
        return {"found": False, "message": f"No employee matches '{name_or_email}'."}
    proj = emp.project.name if emp.project else None
    if not emp.seat:
        return {"found": True, "name": emp.name, "allocated": False, "project": proj}
    seat = emp.seat
    return {
        "found": True, "name": emp.name, "allocated": True, "project": proj,
        "floor": seat.floor, "zone": seat.zone, "bay": seat.bay, "seat_number": seat.seat_number,
        "allocation_date": str(seat.allocation_date),
    }


def tool_available_seats(db: Session, floor: Optional[int] = None, zone: Optional[str] = None) -> dict:
    query = db.query(models.Seat).filter(models.Seat.status == "Available")
    if floor:
        query = query.filter(models.Seat.floor == floor)
    if zone:
        query = query.filter(models.Seat.zone == zone)
    total = query.count()
    sample = [s.seat_number for s in query.limit(8).all()]
    return {"count": total, "sample_seat_numbers": sample, "floor": floor, "zone": zone}


def tool_project_occupancy(db: Session, project_name: str) -> dict:
    proj = db.query(models.Project).filter(func.lower(models.Project.name) == project_name.strip().lower()).first()
    if not proj:
        all_names = [p.name for p in db.query(models.Project).all()]
        return {"found": False, "message": f"No project named '{project_name}'.", "available_projects": all_names}
    occupied = db.query(func.count(models.Seat.id)).filter(
        models.Seat.project_id == proj.id, models.Seat.status == "Occupied"
    ).scalar()
    employees = db.query(func.count(models.Employee.id)).filter(models.Employee.project_id == proj.id).scalar()
    return {"found": True, "project": proj.name, "occupied_seats": occupied, "assigned_employees": employees}


def tool_neighbours(db: Session, employee_name: str) -> dict:
    emp = _find_employee(db, employee_name)
    if not emp or not emp.seat:
        return {"found": False, "message": f"'{employee_name}' isn't a seated employee I can find."}
    seat = emp.seat
    neighbours = (
        db.query(models.Employee)
        .join(models.Seat, models.Seat.employee_id == models.Employee.id)
        .filter(models.Seat.floor == seat.floor, models.Seat.zone == seat.zone, models.Seat.bay == seat.bay, models.Employee.id != emp.id)
        .limit(20).all()
    )
    return {
        "found": True, "name": emp.name, "floor": seat.floor, "zone": seat.zone, "bay": seat.bay,
        "neighbours": [n.name for n in neighbours],
    }


def tool_next_pending_employee(db: Session) -> dict:
    pending = (
        db.query(models.Employee)
        .outerjoin(models.Seat, models.Seat.employee_id == models.Employee.id)
        .filter(models.Seat.id.is_(None))
        .first()
    )
    if not pending:
        return {"found": False, "message": "No pending new joiners right now."}
    return {"found": True, "name": pending.name, "employee_code": pending.employee_code}


def tool_dashboard_summary(db: Session) -> dict:
    total_employees = db.query(func.count(models.Employee.id)).scalar()
    total_seats = db.query(func.count(models.Seat.id)).scalar()
    occupied = db.query(func.count(models.Seat.id)).filter(models.Seat.status == "Occupied").scalar()
    available = db.query(func.count(models.Seat.id)).filter(models.Seat.status == "Available").scalar()
    reserved = db.query(func.count(models.Seat.id)).filter(models.Seat.status == "Reserved").scalar()
    return {
        "total_employees": total_employees, "total_seats": total_seats,
        "occupied": occupied, "available": available, "reserved": reserved,
    }


TOOLS = [
    {"type": "function", "function": {
        "name": "find_employee_seat",
        "description": "Look up whether an employee has a seat, and where, by name or email.",
        "parameters": {"type": "object", "properties": {
            "name_or_email": {"type": "string", "description": "Employee's first name, full name, or email address"},
        }, "required": ["name_or_email"]},
    }},
    {"type": "function", "function": {
        "name": "available_seats",
        "description": "Count and sample the currently available (unoccupied) seats, optionally filtered by floor and/or zone.",
        "parameters": {"type": "object", "properties": {
            "floor": {"type": "integer", "description": "Floor number, 1-5"},
            "zone": {"type": "string", "description": "Zone letter, e.g. A or B"},
        }},
    }},
    {"type": "function", "function": {
        "name": "project_occupancy",
        "description": "Get how many seats are occupied and how many employees are assigned for a given project name.",
        "parameters": {"type": "object", "properties": {
            "project_name": {"type": "string"},
        }, "required": ["project_name"]},
    }},
    {"type": "function", "function": {
        "name": "neighbours",
        "description": "Find who else is seated in the same bay as a given employee.",
        "parameters": {"type": "object", "properties": {
            "employee_name": {"type": "string"},
        }, "required": ["employee_name"]},
    }},
    {"type": "function", "function": {
        "name": "next_pending_employee",
        "description": "Get the next employee who is awaiting seat allocation.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "dashboard_summary",
        "description": "Get overall totals: total employees, total seats, occupied, available, reserved.",
        "parameters": {"type": "object", "properties": {}},
    }},
]

DISPATCH = {
    "find_employee_seat": lambda db, args: tool_find_employee_seat(db, args["name_or_email"]),
    "available_seats": lambda db, args: tool_available_seats(db, args.get("floor"), args.get("zone")),
    "project_occupancy": lambda db, args: tool_project_occupancy(db, args["project_name"]),
    "neighbours": lambda db, args: tool_neighbours(db, args["employee_name"]),
    "next_pending_employee": lambda db, args: tool_next_pending_employee(db),
    "dashboard_summary": lambda db, args: tool_dashboard_summary(db),
}

SYSTEM_PROMPT = (
    "You are the Ethara Facilities seat & project assistant. Answer questions about employee "
    "seating, project assignment, seat availability, and team neighbours. "
    "Always call a tool to look up real data before answering -- never guess or invent facts. "
    "If a tool reports 'found: false', tell the user clearly and, if it lists valid options "
    "(like available_projects), suggest them. Keep answers to 1-2 sentences, in the style of: "
    "'Amit is seated on Floor 2, Zone B, Bay 4, Seat B4-23. He is assigned to Project Indigo.'"
)


def answer_query_llm(db: Session, query: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    for _ in range(4):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto", temperature=0.2,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            return message.content or "I couldn't come up with an answer to that."

        messages.append(message)
        for call in message.tool_calls:
            fn = DISPATCH.get(call.function.name)
            args = json.loads(call.function.arguments or "{}")
            result = fn(db, args) if fn else {"error": "unknown tool"}
            messages.append({
                "role": "tool", "tool_call_id": call.id, "content": json.dumps(result),
            })

    return "I looked that up but couldn't settle on an answer -- try rephrasing your question."
