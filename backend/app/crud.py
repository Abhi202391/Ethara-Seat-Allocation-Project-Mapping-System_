from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from . import models, schemas


# ---------------- Projects ----------------

def create_project(db: Session, payload: schemas.ProjectCreate) -> models.Project:
    existing = db.query(models.Project).filter(models.Project.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project name already exists")
    project = models.Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session):
    return db.query(models.Project).order_by(models.Project.name).all()


def list_project_employees(db: Session, project_id: int):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(models.Employee).filter(models.Employee.project_id == project_id).all()


# ---------------- Employees ----------------

def _next_employee_code(db: Session) -> str:
    last = db.query(models.Employee).order_by(models.Employee.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"EMP-{next_id:05d}"


def create_employee(db: Session, payload: schemas.EmployeeCreate) -> models.Employee:
    existing = db.query(models.Employee).filter(models.Employee.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An employee with this email already exists")

    employee = models.Employee(
        employee_code=payload.employee_code or _next_employee_code(db),
        name=payload.name,
        email=payload.email.lower(),
        department=payload.department,
        role=payload.role,
        joining_date=payload.joining_date,
        status=payload.status or "Active",
        project_id=payload.project_id,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    allocation_note = None
    if payload.auto_allocate:
        try:
            _, allocation_note = allocate_seat(db, employee.id)
            db.refresh(employee)
        except HTTPException:
            allocation_note = "No seats were available at all — employee left pending. Allocate manually once a seat frees up."

    return employee, allocation_note


def update_employee(db: Session, employee_id: int, payload: schemas.EmployeeUpdate) -> models.Employee:
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = data["email"].lower()
        dupe = db.query(models.Employee).filter(
            models.Employee.email == data["email"], models.Employee.id != employee_id
        ).first()
        if dupe:
            raise HTTPException(status_code=400, detail="Email already in use")
    for key, value in data.items():
        setattr(employee, key, value)
    db.commit()
    db.refresh(employee)
    return employee


def deactivate_employee(db: Session, employee_id: int) -> models.Employee:
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.seat:
        release_seat(db, employee_id)
        db.refresh(employee)
    employee.status = "Inactive"
    db.commit()
    db.refresh(employee)
    return employee


def get_employee(db: Session, employee_id: int) -> models.Employee:
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def list_employees(
    db: Session,
    search: Optional[str],
    status_filter: Optional[str],
    page: int,
    page_size: int,
):
    query = db.query(models.Employee)
    if search:
        like = f"%{search.lower()}%"
        query = query.outerjoin(models.Project, models.Employee.project_id == models.Project.id).filter(
            func.lower(models.Employee.name).like(like)
            | func.lower(models.Employee.employee_code).like(like)
            | func.lower(models.Employee.email).like(like)
            | func.lower(models.Project.name).like(like)
        )
    if status_filter == "Pending":
        query = query.outerjoin(models.Seat, models.Seat.employee_id == models.Employee.id).filter(
            models.Seat.id.is_(None)
        )
    elif status_filter == "Allocated":
        query = query.join(models.Seat, models.Seat.employee_id == models.Employee.id)

    total = query.count()
    items = (
        query.order_by(models.Employee.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return total, items


# ---------------- Seats ----------------

def list_seats(db: Session, floor: Optional[int], zone: Optional[str], status_filter: Optional[str]):
    query = db.query(models.Seat).options(joinedload(models.Seat.employee))
    if floor:
        query = query.filter(models.Seat.floor == floor)
    if zone:
        query = query.filter(models.Seat.zone == zone)
    if status_filter:
        query = query.filter(models.Seat.status == status_filter)
    return query.order_by(models.Seat.floor, models.Seat.zone, models.Seat.bay, models.Seat.seat_number).all()


def list_available_seats(db: Session, floor: Optional[int] = None, zone: Optional[str] = None):
    query = db.query(models.Seat).filter(models.Seat.status == "Available")
    if floor:
        query = query.filter(models.Seat.floor == floor)
    if zone:
        query = query.filter(models.Seat.zone == zone)
    return query.all()


def allocate_seat(
    db: Session,
    employee_id: int,
    preferred_floor: Optional[int] = None,
    preferred_zone: Optional[str] = None,
):
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.seat:
        raise HTTPException(status_code=400, detail="Employee already has an active seat")

    note = None
    candidates = []

    # 1) prefer a floor where the employee's project already has the most teammates seated
    if employee.project_id:
        teammate_floor = (
            db.query(models.Seat.floor)
            .filter(models.Seat.project_id == employee.project_id, models.Seat.status == "Occupied")
            .group_by(models.Seat.floor)
            .order_by(func.count(models.Seat.id).desc())
            .first()
        )
        if teammate_floor:
            candidates = list_available_seats(db, floor=teammate_floor[0])

    # 2) explicit caller preference
    if not candidates and (preferred_floor or preferred_zone):
        candidates = list_available_seats(db, floor=preferred_floor, zone=preferred_zone)
        if not candidates:
            note = "No seats available in the preferred zone; allocated from an alternate zone."

    # 3) fall back to any available seat anywhere
    if not candidates:
        candidates = list_available_seats(db)
        if not candidates:
            raise HTTPException(status_code=409, detail="No available seats left")
        if note is None and (employee.project_id or preferred_floor or preferred_zone):
            note = "No seats available near your team; allocated from an alternate zone."

    seat = candidates[0]
    today = date.today()
    seat.status = "Occupied"
    seat.employee_id = employee.id
    seat.project_id = employee.project_id
    seat.allocation_date = today

    db.add(models.SeatAllocation(
        employee_id=employee.id,
        seat_id=seat.id,
        project_id=employee.project_id,
        allocation_status="active",
        allocation_date=today,
    ))
    db.commit()
    db.refresh(seat)
    return seat, note


def release_seat(db: Session, employee_id: int):
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    seat = employee.seat
    if not seat:
        raise HTTPException(status_code=400, detail="Employee has no active seat")

    seat.status = "Available"
    seat.employee_id = None
    seat.project_id = None
    seat.allocation_date = None

    allocation = (
        db.query(models.SeatAllocation)
        .filter(models.SeatAllocation.seat_id == seat.id, models.SeatAllocation.allocation_status == "active")
        .order_by(models.SeatAllocation.id.desc())
        .first()
    )
    if allocation:
        allocation.allocation_status = "released"
        allocation.released_date = date.today()

    db.commit()
    db.refresh(seat)
    return seat


# ---------------- Dashboard ----------------

def dashboard_summary(db: Session) -> schemas.DashboardSummary:
    total_employees = db.query(func.count(models.Employee.id)).scalar() or 0
    total_seats = db.query(func.count(models.Seat.id)).scalar() or 0
    occupied = db.query(func.count(models.Seat.id)).filter(models.Seat.status == "Occupied").scalar() or 0
    available = db.query(func.count(models.Seat.id)).filter(models.Seat.status == "Available").scalar() or 0
    reserved = db.query(func.count(models.Seat.id)).filter(models.Seat.status == "Reserved").scalar() or 0
    maintenance = db.query(func.count(models.Seat.id)).filter(models.Seat.status == "Maintenance").scalar() or 0
    pending = (
        db.query(func.count(models.Employee.id))
        .outerjoin(models.Seat, models.Seat.employee_id == models.Employee.id)
        .filter(models.Seat.id.is_(None))
        .scalar()
        or 0
    )
    return schemas.DashboardSummary(
        total_employees=total_employees,
        total_seats=total_seats,
        occupied=occupied,
        available=available,
        reserved=reserved,
        maintenance=maintenance,
        pending=pending,
    )


def dashboard_project_utilization(db: Session):
    rows = (
        db.query(
            models.Project.id,
            models.Project.name,
            models.Project.manager_name,
            models.Project.status,
            func.count(func.distinct(models.Employee.id)).label("employee_count"),
            func.count(func.distinct(models.Seat.id)).label("seat_count"),
        )
        .outerjoin(models.Employee, models.Employee.project_id == models.Project.id)
        .outerjoin(
            models.Seat,
            (models.Seat.project_id == models.Project.id) & (models.Seat.status == "Occupied"),
        )
        .group_by(models.Project.id)
        .order_by(func.count(func.distinct(models.Employee.id)).desc())
        .all()
    )
    return [
        schemas.ProjectUtilizationOut(
            id=r.id,
            name=r.name,
            manager_name=r.manager_name or "",
            status=r.status,
            employee_count=r.employee_count,
            seat_count=r.seat_count,
        )
        for r in rows
    ]


def dashboard_floor_utilization(db: Session):
    rows = (
        db.query(
            models.Seat.floor,
            func.count(models.Seat.id).label("total"),
            func.sum(case((models.Seat.status == "Occupied", 1), else_=0)).label("occupied"),
        )
        .group_by(models.Seat.floor)
        .order_by(models.Seat.floor)
        .all()
    )
    result = []
    for r in rows:
        occ = r.occupied or 0
        pct = round((occ / r.total) * 100, 1) if r.total else 0.0
        result.append(schemas.FloorUtilizationOut(floor=r.floor, total=r.total, occupied=occ, pct=pct))
    return result
