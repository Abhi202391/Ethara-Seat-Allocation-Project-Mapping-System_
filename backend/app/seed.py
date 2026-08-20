"""Deterministic seed data generator.

Sized to satisfy the assessment's minimums:
  - 5,000 employees            (spec: 5,000)
  - 5 floors x 2 zones = 10 zones   (spec: >= 10 zones)
  - 5 x 2 x 20 x 28 = 5,600 seats   (spec: >= 5,500)
  - 11 projects                (spec: >= 10)
  - ~168 reserved seats        (spec: >= 100)
  - ~550 available seats after allocation (spec: >= 500)
  - 180 pending employees      (spec: >= 50)

Run with:  python -m app.seed
"""

import random
from datetime import date, timedelta

from .database import Base, SessionLocal, engine
from . import models, security

DEMO_MANAGER_EMAIL = "manager@ethara.ai"
DEMO_MANAGER_PASSWORD = "Manager@123"
DEMO_EMPLOYEE_EMAIL = "employee@ethara.ai"
DEMO_EMPLOYEE_PASSWORD = "Employee@123"

FIRST_NAMES = [
    "Amit", "Priya", "Rahul", "Sneha", "Vikram", "Anjali", "Rohan", "Kavya", "Arjun", "Divya",
    "Karan", "Meera", "Nikhil", "Pooja", "Sanjay", "Isha", "Varun", "Ritu", "Aditya", "Neha",
    "Manish", "Shreya", "Rajesh", "Tanya", "Suresh", "Anita", "Deepak", "Swati", "Vivek", "Nisha",
    "Harsh", "Ayesha", "Gaurav", "Kritika", "Siddharth", "Simran", "Ashok", "Radhika", "Mohit", "Preeti",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Iyer", "Nair", "Reddy", "Gupta", "Malhotra", "Chopra", "Rao",
    "Menon", "Kapoor", "Joshi", "Desai", "Bhatt", "Pillai", "Saxena", "Mishra", "Agarwal", "Kulkarni",
]
DEPARTMENTS = ["Engineering", "QA", "Product", "Design", "Data", "DevOps", "Support", "HR", "Finance", "Sales"]
ROLES = [
    "Software Engineer", "Senior Engineer", "QA Analyst", "Product Manager", "UX Designer",
    "Data Analyst", "DevOps Engineer", "Support Specialist", "HR Executive", "Team Lead",
]
PROJECT_DESCRIPTIONS = {
    "Indigo": "Enterprise resource planning suite for supply chain operations",
    "Indreed": "Talent sourcing and recruitment analytics platform",
    "Mydreed": "Employee self-service HR portal and benefits management",
    "Preed": "Real-time payments and settlement infrastructure",
    "Serfy": "Customer support ticketing and live-chat platform",
    "Oreed": "Order management and fulfillment tracking system",
    "Bedegreed": "Internal budgeting and financial forecasting tool",
    "Opreed": "Operations dashboard for facilities and asset monitoring",
    "Serry": "Sales CRM and pipeline forecasting application",
    "Kaary": "Logistics and fleet route optimization engine",
    "Mered": "Marketing campaign analytics and attribution platform",
}
PROJECT_NAMES = list(PROJECT_DESCRIPTIONS.keys())

FLOORS = [1, 2, 3, 4, 5]
ZONES = ["A", "B"]
BAYS_PER_ZONE = 20
SEATS_PER_BAY = 28

EMP_COUNT = 5000
PENDING_COUNT = 180
RESERVED_RATIO = 0.03
MAINTENANCE_RATIO = 0.015


def run(seed: int = 42):
    random.seed(seed)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ---- projects ----
        projects = []
        for name in PROJECT_NAMES:
            p = models.Project(
                name=name,
                description=PROJECT_DESCRIPTIONS[name],
                manager_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                status="Active",
            )
            db.add(p)
            projects.append(p)
        db.commit()
        for p in projects:
            db.refresh(p)

        # ---- seats ----
        seats = []
        for floor in FLOORS:
            for zone in ZONES:
                for bay in range(1, BAYS_PER_ZONE + 1):
                    for s in range(1, SEATS_PER_BAY + 1):
                        global_num = (bay - 1) * SEATS_PER_BAY + s
                        seats.append(models.Seat(
                            floor=floor, zone=zone, bay=bay,
                            seat_number=f"{zone}{bay}-{global_num:03d}",
                            status="Available",
                        ))
        db.add_all(seats)
        db.commit()
        for s in seats:
            db.refresh(s)

        shuffled = seats[:]
        random.shuffle(shuffled)
        reserved_target = int(len(seats) * RESERVED_RATIO)
        maint_target = int(len(seats) * MAINTENANCE_RATIO)
        for seat in shuffled[:reserved_target]:
            seat.status = "Reserved"
        for seat in shuffled[reserved_target:reserved_target + maint_target]:
            seat.status = "Maintenance"
        db.commit()

        seats_by_floor = {f: [s for s in seats if s.floor == f and s.status == "Available"] for f in FLOORS}

        def take_seat(preferred_floor):
            pool = seats_by_floor.get(preferred_floor) or []
            if not pool:
                for floor_seats in seats_by_floor.values():
                    if floor_seats:
                        pool = floor_seats
                        break
            if not pool:
                return None
            idx = random.randrange(len(pool))
            return pool.pop(idx)

        # ---- employees ----
        today = date.today()
        for i in range(1, EMP_COUNT + 1):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            project = random.choice(projects)
            dept = random.choice(DEPARTMENTS)
            joining = today - timedelta(days=random.randint(0, 500))
            is_pending = i > EMP_COUNT - PENDING_COUNT

            emp = models.Employee(
                employee_code=f"EMP-{i:05d}",
                name=f"{first} {last}",
                email=f"{first}.{last}{i}@ethara.ai".lower(),
                department=dept,
                role=random.choice(ROLES),
                joining_date=joining,
                status="Active",
                project_id=project.id,
            )
            db.add(emp)
            db.flush()

            if not is_pending:
                seat = take_seat((i % 5) + 1)
                if seat:
                    seat.status = "Occupied"
                    seat.employee_id = emp.id
                    seat.project_id = project.id
                    seat.allocation_date = joining
                    db.add(models.SeatAllocation(
                        employee_id=emp.id, seat_id=seat.id, project_id=project.id,
                        allocation_status="active", allocation_date=joining,
                    ))

            if i % 500 == 0:
                db.commit()

        db.commit()

        # ---- demo auth accounts ----
        first_employee = db.query(models.Employee).order_by(models.Employee.id).first()
        mgr_hash, mgr_salt = security.hash_password(DEMO_MANAGER_PASSWORD)
        db.add(models.User(
            email=DEMO_MANAGER_EMAIL, password_hash=mgr_hash, password_salt=mgr_salt, role="manager",
        ))
        emp_hash, emp_salt = security.hash_password(DEMO_EMPLOYEE_PASSWORD)
        db.add(models.User(
            email=DEMO_EMPLOYEE_EMAIL, password_hash=emp_hash, password_salt=emp_salt, role="employee",
            employee_id=first_employee.id if first_employee else None,
        ))
        db.commit()

        total_seats = len(seats)
        available = sum(1 for s in seats if s.status == "Available")
        reserved = sum(1 for s in seats if s.status == "Reserved")
        maintenance = sum(1 for s in seats if s.status == "Maintenance")
        occupied = sum(1 for s in seats if s.status == "Occupied")
        print(
            f"Seeded {EMP_COUNT} employees ({PENDING_COUNT} pending), {total_seats} seats "
            f"across {len(FLOORS)} floors x {len(ZONES)} zones, {len(projects)} projects.\n"
            f"Seat status -> available: {available}, occupied: {occupied}, "
            f"reserved: {reserved}, maintenance: {maintenance}"
        )
        print(
            f"Demo accounts -> Manager: {DEMO_MANAGER_EMAIL} / {DEMO_MANAGER_PASSWORD} | "
            f"Employee: {DEMO_EMPLOYEE_EMAIL} / {DEMO_EMPLOYEE_PASSWORD} "
            f"(linked to {first_employee.name if first_employee else 'n/a'})"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
