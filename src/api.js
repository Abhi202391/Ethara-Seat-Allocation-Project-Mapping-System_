const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function normalizeProject(p) {
  return { id: p.id, name: p.name, manager: p.manager_name, status: p.status };
}

export function normalizeSeat(s) {
  return {
    id: s.id,
    floor: s.floor,
    zone: s.zone,
    bay: s.bay,
    seatNumber: s.seat_number,
    status: s.status,
    employeeId: s.employee_id,
    employeeName: s.employee_name,
    projectId: s.project_id,
    allocationDate: s.allocation_date,
  };
}

export function normalizeEmployee(e) {
  return {
    id: e.id,
    code: e.employee_code,
    name: e.name,
    email: e.email,
    department: e.department,
    role: e.role,
    joiningDate: e.joining_date,
    status: e.status,
    projectId: e.project_id,
    seatId: e.seat ? e.seat.id : null,
    seat: e.seat ? normalizeSeat(e.seat) : null,
  };
}

export const api = {
  listProjects: async () => (await request("/projects")).map(normalizeProject),

  listEmployees: async ({ search = "", status = "All", page = 1, pageSize = 12 } = {}) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (search) params.set("search", search);
    if (status && status !== "All") params.set("status", status);
    const data = await request(`/employees?${params.toString()}`);
    return { total: data.total, page: data.page, pageSize: data.page_size, items: data.items.map(normalizeEmployee) };
  },

  createEmployee: async (payload) => {
    const data = await request("/employees", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return { employee: normalizeEmployee(data.employee), note: data.allocation_note };
  },

  updateEmployee: async (id, payload) =>
    normalizeEmployee(
      await request(`/employees/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      })
    ),

  deactivateEmployee: async (id) =>
    normalizeEmployee(await request(`/employees/${id}`, { method: "DELETE" })),

  importEmployeesCsv: async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE_URL}/employees/import-csv`, { method: "POST", body: form });
    if (!res.ok) throw new Error("CSV import failed");
    return res.json();
  },

  listSeats: async ({ floor, zone, status } = {}) => {
    const params = new URLSearchParams();
    if (floor && floor !== "All") params.set("floor", String(floor));
    if (zone && zone !== "All") params.set("zone", zone);
    if (status && status !== "All") params.set("status", status);
    const data = await request(`/seats?${params.toString()}`);
    return data.map(normalizeSeat);
  },

  allocateSeat: async (employeeId, seatId = null) => {
    const data = await request("/seats/allocate", {
      method: "POST",
      body: JSON.stringify({ employee_id: employeeId, seat_id: seatId }),
    });
    return { seat: normalizeSeat(data.seat), note: data.note };
  },

  suggestSeats: async ({ projectId, preferredFloor, preferredZone, limit = 8 } = {}) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (projectId) params.set("project_id", String(projectId));
    if (preferredFloor) params.set("preferred_floor", String(preferredFloor));
    if (preferredZone) params.set("preferred_zone", preferredZone);
    const data = await request(`/seats/suggestions?${params.toString()}`);
    return data.map((s) => ({ seat: normalizeSeat(s.seat), reason: s.reason }));
  },

  releaseSeat: async (employeeId) =>
    normalizeSeat(
      await request("/seats/release", {
        method: "POST",
        body: JSON.stringify({ employee_id: employeeId }),
      })
    ),

  listSeatAllocations: async ({ search = "", status = "All", page = 1, pageSize = 15 } = {}) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (search) params.set("search", search);
    if (status === "Active") params.set("status", "active");
    if (status === "Released") params.set("status", "released");
    const data = await request(`/seat-allocations?${params.toString()}`);
    const items = data.items.map((r) => ({
      id: r.id,
      employeeId: r.employee_id,
      employeeName: r.employee_name,
      seatId: r.seat_id,
      seatNumber: r.seat_number,
      projectId: r.project_id,
      projectName: r.project_name,
      status: r.allocation_status,
      allocationDate: r.allocation_date,
      releasedDate: r.released_date,
    }));
    return { total: data.total, page: data.page, pageSize: data.page_size, items };
  },

  dashboardSummary: async () => {
    const d = await request("/dashboard/summary");
    return {
      totalEmployees: d.total_employees,
      totalSeats: d.total_seats,
      occupied: d.occupied,
      available: d.available,
      reserved: d.reserved,
      maintenance: d.maintenance,
      pending: d.pending,
    };
  },

  dashboardProjectUtilization: async () => {
    const rows = await request("/dashboard/project-utilization");
    return rows.map((r) => ({
      id: r.id,
      name: r.name,
      description: r.description,
      manager: r.manager_name,
      status: r.status,
      createdAt: r.created_at,
      empCount: r.employee_count,
      seatCount: r.seat_count,
    }));
  },

  dashboardFloorUtilization: async () => {
    const rows = await request("/dashboard/floor-utilization");
    return rows.map((r) => ({ floor: r.floor, total: r.total, occupied: r.occupied, pct: r.pct }));
  },

  aiQuery: async (query) => (await request("/ai/query", { method: "POST", body: JSON.stringify({ query } ) })).answer,
};
