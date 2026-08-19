from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, default="")
    manager_name = Column(String, default="")
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=datetime.utcnow)

    employees = relationship("Employee", back_populates="project")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    department = Column(String, default="")
    role = Column(String, default="")
    joining_date = Column(Date, nullable=False)
    status = Column(String, default="Active")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="employees")
    seat = relationship("Seat", back_populates="employee", uselist=False)


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("floor", "zone", "seat_number", name="uq_seat_position"),)

    id = Column(Integer, primary_key=True, index=True)
    floor = Column(Integer, nullable=False, index=True)
    zone = Column(String, nullable=False, index=True)
    bay = Column(Integer, nullable=False)
    seat_number = Column(String, nullable=False)
    status = Column(String, default="Available", index=True)  # Available / Occupied / Reserved / Maintenance
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    allocation_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="seat", foreign_keys=[employee_id])

    @property
    def employee_name(self):
        return self.employee.name if self.employee else None


class SeatAllocation(Base):
    __tablename__ = "seat_allocations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    allocation_status = Column(String, default="active")  # active / released
    allocation_date = Column(Date, nullable=False)
    released_date = Column(Date, nullable=True)
