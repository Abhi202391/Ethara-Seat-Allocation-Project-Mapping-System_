import csv
import io
from datetime import date
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import ai_assistant, crud, models, schemas
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ethara Seat Allocation & Project Mapping API",
    description="Backend for the Ethara Seat Allocation & Project Mapping System assessment.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------- Employee APIs ----------------

@app.post("/employees", response_model=schemas.EmployeeCreateResponse)
def create_employee(payload: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    employee, allocation_note = crud.create_employee(db, payload)
    return schemas.EmployeeCreateResponse(employee=schemas.EmployeeOut.model_validate(employee), allocation_note=allocation_note)


@app.get("/employees", response_model=schemas.EmployeeListResponse)
def list_employees(
    search: Optional[str] = None,
    status: Optional[str] = Query(None, description="All | Allocated | Pending"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total, items = crud.list_employees(db, search, status, page, page_size)
    return schemas.EmployeeListResponse(total=total, page=page, page_size=page_size, items=items)


@app.get("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    return crud.get_employee(db, employee_id)


@app.put("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(employee_id: int, payload: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    return crud.update_employee(db, employee_id, payload)


@app.delete("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    return crud.deactivate_employee(db, employee_id)


@app.post("/employees/import-csv")
async def import_employees_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Bulk-add employees from a CSV with columns: name,email,department,role,joining_date,project"""
    raw = await file.read()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    created, skipped = 0, []
    for row in reader:
        try:
            project = None
            project_name = (row.get("project") or "").strip()
            if project_name:
                project = db.query(models.Project).filter(models.Project.name == project_name).first()
            payload = schemas.EmployeeCreate(
                name=(row.get("name") or "").strip(),
                email=(row.get("email") or "").strip().lower(),
                department=(row.get("department") or "").strip(),
                role=(row.get("role") or "").strip(),
                joining_date=(row.get("joining_date") or str(date.today())).strip(),
                project_id=project.id if project else None,
            )
            crud.create_employee(db, payload)
            created += 1
        except HTTPException as e:
            skipped.append({"row": row.get("email", "?"), "reason": e.detail})
        except Exception as e:  # malformed row — keep import going
            skipped.append({"row": row.get("email", "?"), "reason": str(e)})
    return {"created": created, "skipped": skipped}


# ---------------- Project APIs ----------------

@app.post("/projects", response_model=schemas.ProjectOut)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    return crud.create_project(db, payload)


@app.get("/projects", response_model=List[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return crud.list_projects(db)


@app.get("/projects/{project_id}/employees", response_model=List[schemas.EmployeeOut])
def list_project_employees(project_id: int, db: Session = Depends(get_db)):
    return crud.list_project_employees(db, project_id)


# ---------------- Seat APIs ----------------

@app.post("/seats", response_model=schemas.SeatOut)
def create_seat(payload: schemas.SeatCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Seat).filter(
        models.Seat.floor == payload.floor,
        models.Seat.zone == payload.zone,
        models.Seat.seat_number == payload.seat_number,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A seat with this floor/zone/number already exists")
    seat = models.Seat(**payload.model_dump())
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return seat


@app.get("/seats", response_model=List[schemas.SeatOut])
def list_seats(
    floor: Optional[int] = None,
    zone: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.list_seats(db, floor, zone, status)


@app.get("/seats/available", response_model=List[schemas.SeatOut])
def list_available_seats(floor: Optional[int] = None, zone: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.list_available_seats(db, floor, zone)


@app.get("/seats/suggestions", response_model=List[schemas.SeatSuggestion])
def suggest_seats(
    project_id: Optional[int] = None,
    preferred_floor: Optional[int] = None,
    preferred_zone: Optional[str] = None,
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
):
    ranked = crud.suggest_seats(db, project_id, preferred_floor, preferred_zone, limit)
    return [schemas.SeatSuggestion(seat=schemas.SeatOut.model_validate(seat), reason=reason) for seat, reason in ranked]


@app.post("/seats/allocate", response_model=schemas.AllocateResponse)
def allocate_seat(payload: schemas.AllocateRequest, db: Session = Depends(get_db)):
    seat, note = crud.allocate_seat(
        db, payload.employee_id, payload.preferred_floor, payload.preferred_zone, seat_id=payload.seat_id
    )
    return schemas.AllocateResponse(seat=schemas.SeatOut.model_validate(seat), note=note)


@app.post("/seats/release", response_model=schemas.SeatOut)
def release_seat(payload: schemas.ReleaseRequest, db: Session = Depends(get_db)):
    return crud.release_seat(db, payload.employee_id)


# ---------------- Seat Allocation history (audit trail) ----------------

@app.get("/seat-allocations", response_model=schemas.SeatAllocationListResponse)
def list_seat_allocations(
    employee_id: Optional[int] = None,
    seat_id: Optional[int] = None,
    project_id: Optional[int] = None,
    status: Optional[str] = Query(None, description="active | released"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total, rows = crud.list_seat_allocations(db, employee_id, seat_id, project_id, status, search, page, page_size)
    items = [
        schemas.SeatAllocationOut(
            id=r.id,
            employee_id=r.employee_id,
            employee_name=r.employee.name,
            seat_id=r.seat_id,
            seat_number=r.seat.seat_number,
            project_id=r.project_id,
            project_name=r.project.name if r.project else None,
            allocation_status=r.allocation_status,
            allocation_date=r.allocation_date,
            released_date=r.released_date,
        )
        for r in rows
    ]
    return schemas.SeatAllocationListResponse(total=total, page=page, page_size=page_size, items=items)


# ---------------- Dashboard APIs ----------------

@app.get("/dashboard/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return crud.dashboard_summary(db)


@app.get("/dashboard/project-utilization", response_model=List[schemas.ProjectUtilizationOut])
def dashboard_project_utilization(db: Session = Depends(get_db)):
    return crud.dashboard_project_utilization(db)


@app.get("/dashboard/floor-utilization", response_model=List[schemas.FloorUtilizationOut])
def dashboard_floor_utilization(db: Session = Depends(get_db)):
    return crud.dashboard_floor_utilization(db)


# ---------------- AI Assistant API ----------------

@app.post("/ai/query", response_model=schemas.AIQueryResponse)
def ai_query(payload: schemas.AIQueryRequest, db: Session = Depends(get_db)):
    answer = ai_assistant.answer_query(db, payload.query)
    return schemas.AIQueryResponse(answer=answer)
