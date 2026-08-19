from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = ""
    manager_name: Optional[str] = ""
    status: Optional[str] = "Active"


class ProjectCreate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    floor: int
    zone: str
    bay: int
    seat_number: str
    status: str
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    project_id: Optional[int] = None
    allocation_date: Optional[date] = None


class EmployeeBase(BaseModel):
    name: str
    email: str
    department: Optional[str] = ""
    role: Optional[str] = ""
    joining_date: date
    status: Optional[str] = "Active"
    project_id: Optional[int] = None


class EmployeeCreate(EmployeeBase):
    employee_code: Optional[str] = None
    auto_allocate: Optional[bool] = True
    seat_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    joining_date: Optional[date] = None
    status: Optional[str] = None
    project_id: Optional[int] = None


class EmployeeOut(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_code: str
    created_at: datetime
    updated_at: datetime
    seat: Optional[SeatOut] = None


class EmployeeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[EmployeeOut]


class EmployeeCreateResponse(BaseModel):
    employee: EmployeeOut
    allocation_note: Optional[str] = None


class SeatCreate(BaseModel):
    floor: int
    zone: str
    bay: int
    seat_number: str
    status: Optional[str] = "Available"


class AllocateRequest(BaseModel):
    employee_id: int
    seat_id: Optional[int] = None
    preferred_floor: Optional[int] = None
    preferred_zone: Optional[str] = None


class AllocateResponse(BaseModel):
    seat: SeatOut
    note: Optional[str] = None


class SeatSuggestion(BaseModel):
    seat: SeatOut
    reason: str


class ReleaseRequest(BaseModel):
    employee_id: int


class SeatAllocationOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    seat_id: int
    seat_number: str
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    allocation_status: str
    allocation_date: date
    released_date: Optional[date] = None


class SeatAllocationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[SeatAllocationOut]


class DashboardSummary(BaseModel):
    total_employees: int
    total_seats: int
    occupied: int
    available: int
    reserved: int
    maintenance: int
    pending: int


class ProjectUtilizationOut(BaseModel):
    id: int
    name: str
    description: str
    manager_name: str
    status: str
    created_at: datetime
    employee_count: int
    seat_count: int


class FloorUtilizationOut(BaseModel):
    floor: int
    total: int
    occupied: int
    pct: float


class AIQueryRequest(BaseModel):
    query: str


class AIQueryResponse(BaseModel):
    answer: str
