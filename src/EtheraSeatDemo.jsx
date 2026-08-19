import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Search, MapPin, Users, Briefcase, MessageSquare,
  CheckCircle2, Clock, AlertTriangle, LayoutGrid,
  UserPlus, X, Send, Plus, Upload, Loader2, Pencil, Ban
} from "lucide-react";
import { api } from "./api";

const DEPARTMENTS = ["Engineering", "QA", "Product", "Design", "Data", "DevOps", "Support", "HR", "Finance", "Sales"];
const ROLES = [
  "Software Engineer", "Senior Engineer", "QA Analyst", "Product Manager", "UX Designer",
  "Data Analyst", "DevOps Engineer", "Support Specialist", "HR Executive", "Team Lead",
];
const FLOORS = [1, 2, 3, 4, 5];
const ZONES = ["A", "B"];
const STATUS = { AVAILABLE: "Available", OCCUPIED: "Occupied", RESERVED: "Reserved", MAINTENANCE: "Maintenance" };
const PAGE_SIZE = 12;

function StatusBadge({ status }) {
  const map = {
    [STATUS.AVAILABLE]: "bg-emerald-400/15 text-emerald-300 border-emerald-400/30",
    [STATUS.OCCUPIED]: "bg-amber-400/15 text-amber-300 border-amber-400/30",
    [STATUS.RESERVED]: "bg-sky-400/15 text-sky-300 border-sky-400/30",
    [STATUS.MAINTENANCE]: "bg-rose-400/15 text-rose-300 border-rose-400/30",
    Pending: "bg-fuchsia-400/15 text-fuchsia-300 border-fuchsia-400/30",
    Inactive: "bg-rose-400/15 text-rose-300 border-rose-400/30",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-[11px] font-mono uppercase tracking-wide ${map[status] || ""}`}>
      {status}
    </span>
  );
}

function Card({ label, value, icon: Icon, tint, loading }) {
  return (
    <div className="rounded-lg border border-[#2E1F47] bg-[#000000] p-4 flex items-center justify-between">
      <div>
        <div className="text-[11px] uppercase tracking-widest text-[#A99BC4] font-mono">{label}</div>
        <div className="text-2xl font-semibold text-[#F3EEFB] mt-1 font-mono">{loading ? "…" : value}</div>
      </div>
      <Icon size={20} className={tint} />
    </div>
  );
}

export default function EtheraSeatDemo() {
  const [tab, setTab] = useState("dashboard");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [projects, setProjects] = useState([]);

  const [summary, setSummary] = useState(null);
  const [projectUtilization, setProjectUtilization] = useState([]);
  const [floorUtilization, setFloorUtilization] = useState([]);
  const [dashboardLoading, setDashboardLoading] = useState(true);

  const [empQuery, setEmpQuery] = useState("");
  const [empStatusFilter, setEmpStatusFilter] = useState("All");
  const [page, setPage] = useState(0);
  const [employees, setEmployees] = useState([]);
  const [employeeTotal, setEmployeeTotal] = useState(0);
  const [employeesLoading, setEmployeesLoading] = useState(true);

  const [seatFloorFilter, setSeatFloorFilter] = useState("1");
  const [seatZoneFilter, setSeatZoneFilter] = useState("All");
  const [seatStatusFilter, setSeatStatusFilter] = useState("All");
  const [seats, setSeats] = useState([]);
  const [seatsLoading, setSeatsLoading] = useState(true);

  const [aiInput, setAiInput] = useState("");
  const [aiLog, setAiLog] = useState([
    { role: "system", text: "Ask me things like “where is Amit seated”, “available seats on floor 3”, or “how many seats occupied for project Indigo”." },
  ]);
  const [aiBusy, setAiBusy] = useState(false);

  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState({
    name: "", email: "", department: DEPARTMENTS[0], role: ROLES[0],
    joiningDate: new Date().toISOString().slice(0, 10), projectId: "", autoAllocate: true,
  });
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addError, setAddError] = useState("");

  const [editingEmployee, setEditingEmployee] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState("");

  const fileInputRef = useRef(null);
  const [csvMessage, setCsvMessage] = useState("");
  const [csvBusy, setCsvBusy] = useState(false);

  const projectById = useMemo(() => Object.fromEntries(projects.map((p) => [p.id, p])), [projects]);
  const totalPages = Math.max(1, Math.ceil(employeeTotal / PAGE_SIZE));

  async function loadProjects() {
    try {
      setProjects(await api.listProjects());
    } catch (e) {
      setError(e.message);
    }
  }

  async function loadDashboard() {
    setDashboardLoading(true);
    try {
      const [s, pu, fu] = await Promise.all([
        api.dashboardSummary(),
        api.dashboardProjectUtilization(),
        api.dashboardFloorUtilization(),
      ]);
      setSummary(s);
      setProjectUtilization(pu);
      setFloorUtilization(fu);
    } catch (e) {
      setError(e.message);
    } finally {
      setDashboardLoading(false);
    }
  }

  async function loadEmployees() {
    setEmployeesLoading(true);
    try {
      const res = await api.listEmployees({ search: empQuery, status: empStatusFilter, page: page + 1, pageSize: PAGE_SIZE });
      setEmployees(res.items);
      setEmployeeTotal(res.total);
    } catch (e) {
      setError(e.message);
    } finally {
      setEmployeesLoading(false);
    }
  }

  async function loadSeats() {
    setSeatsLoading(true);
    try {
      setSeats(await api.listSeats({ floor: seatFloorFilter, zone: seatZoneFilter, status: seatStatusFilter }));
    } catch (e) {
      setError(e.message);
    } finally {
      setSeatsLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
    loadDashboard();
  }, []);

  useEffect(() => {
    const t = setTimeout(loadEmployees, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empQuery, empStatusFilter, page]);

  useEffect(() => {
    loadSeats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seatFloorFilter, seatZoneFilter, seatStatusFilter]);

  async function allocateSeat(employeeId) {
    try {
      const { note } = await api.allocateSeat(employeeId);
      const empName = employees.find((e) => e.id === employeeId)?.name || "Employee";
      setNotice(note ? `${empName}: ${note}` : "");
      await Promise.all([loadEmployees(), loadDashboard()]);
    } catch (e) {
      setError(e.message);
    }
  }

  async function releaseSeat(employeeId) {
    try {
      await api.releaseSeat(employeeId);
      await Promise.all([loadEmployees(), loadDashboard()]);
    } catch (e) {
      setError(e.message);
    }
  }

  async function submitAiQuery(e) {
    e.preventDefault();
    const q = aiInput.trim();
    if (!q || aiBusy) return;
    setAiLog((log) => [...log, { role: "user", text: q }]);
    setAiInput("");
    setAiBusy(true);
    try {
      const answer = await api.aiQuery(q);
      setAiLog((log) => [...log, { role: "assistant", text: answer }]);
    } catch (err) {
      setAiLog((log) => [...log, { role: "assistant", text: `Sorry, I hit an error reaching the assistant: ${err.message}` }]);
    } finally {
      setAiBusy(false);
    }
  }

  function openAddModal() {
    setAddForm({
      name: "", email: "", department: DEPARTMENTS[0], role: ROLES[0],
      joiningDate: new Date().toISOString().slice(0, 10), projectId: projects[0]?.id ?? "", autoAllocate: true,
    });
    setAddError("");
    setShowAddModal(true);
  }

  async function submitAddEmployee(e) {
    e.preventDefault();
    setAddSubmitting(true);
    setAddError("");
    try {
      const { employee, note } = await api.createEmployee({
        name: addForm.name,
        email: addForm.email,
        department: addForm.department,
        role: addForm.role,
        joining_date: addForm.joiningDate,
        project_id: addForm.projectId ? Number(addForm.projectId) : null,
        auto_allocate: addForm.autoAllocate,
      });
      setNotice(note ? `${employee.name}: ${note}` : "");
      setShowAddModal(false);
      setPage(0);
      await Promise.all([loadEmployees(), loadDashboard()]);
    } catch (err) {
      setAddError(err.message);
    } finally {
      setAddSubmitting(false);
    }
  }

  function openEditModal(emp) {
    setEditingEmployee(emp);
    setEditForm({
      name: emp.name,
      email: emp.email,
      department: emp.department || DEPARTMENTS[0],
      role: emp.role || ROLES[0],
      joiningDate: emp.joiningDate,
      status: emp.status,
      projectId: emp.projectId ?? "",
    });
    setEditError("");
  }

  async function submitEditEmployee(e) {
    e.preventDefault();
    if (!editingEmployee) return;
    setEditSubmitting(true);
    setEditError("");
    try {
      await api.updateEmployee(editingEmployee.id, {
        name: editForm.name,
        email: editForm.email,
        department: editForm.department,
        role: editForm.role,
        joining_date: editForm.joiningDate,
        status: editForm.status,
        project_id: editForm.projectId ? Number(editForm.projectId) : null,
      });
      setEditingEmployee(null);
      await Promise.all([loadEmployees(), loadDashboard()]);
    } catch (err) {
      setEditError(err.message);
    } finally {
      setEditSubmitting(false);
    }
  }

  async function deactivateEmployee(emp) {
    if (!window.confirm(`Deactivate ${emp.name}? This releases their seat if they have one.`)) return;
    try {
      await api.deactivateEmployee(emp.id);
      await Promise.all([loadEmployees(), loadDashboard()]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCsvSelected(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvBusy(true);
    setCsvMessage("");
    try {
      const result = await api.importEmployeesCsv(file);
      const skippedText = result.skipped.length ? `, skipped ${result.skipped.length}` : "";
      setCsvMessage(`Imported ${result.created} employee${result.created === 1 ? "" : "s"}${skippedText}.`);
      setPage(0);
      await Promise.all([loadEmployees(), loadDashboard()]);
    } catch (err) {
      setCsvMessage(`CSV import failed: ${err.message}`);
    } finally {
      setCsvBusy(false);
      e.target.value = "";
    }
  }

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: LayoutGrid },
    { id: "employees", label: "Employees", icon: Users },
    { id: "seats", label: "Seat Map", icon: MapPin },
    { id: "projects", label: "Projects", icon: Briefcase },
    { id: "ai", label: "AI Assistant", icon: MessageSquare },
  ];

  return (
    <div className="min-h-screen bg-[#000000] text-[#F3EEFB] font-sans">
      {/* header */}
      <div className="border-b border-[#241934] bg-[#000000] sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-5 py-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono tracking-[0.25em] text-[#B563FA] uppercase">Ethara · Facilities</div>
            <h1 className="text-lg font-semibold tracking-tight text-[#B563FA]">Seat Allocation &amp; Project Mapping</h1>
          </div>
          <div className="hidden sm:flex items-center gap-1 text-[11px] font-mono text-[#A99BC4] border border-[#2E1F47] rounded px-2 py-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
            live API · {summary ? summary.totalEmployees : "…"} employees · {summary ? summary.totalSeats : "…"} seats
          </div>
        </div>
        <div className="max-w-6xl mx-auto px-5 flex gap-1 overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); }}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 whitespace-nowrap transition-colors ${
                tab === t.id ? "border-[#B563FA] text-[#F3EEFB]" : "border-transparent text-[#A99BC4] hover:text-[#F3EEFB]"
              }`}
            >
              <t.icon size={15} /> {t.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="max-w-6xl mx-auto px-5 pt-3">
          <div className="flex items-center justify-between gap-3 rounded-lg border border-rose-400/30 bg-rose-400/10 text-rose-300 text-sm px-3 py-2">
            <span>{error}</span>
            <button onClick={() => setError("")} className="text-rose-300 hover:text-rose-100"><X size={14} /></button>
          </div>
        </div>
      )}

      {notice && (
        <div className="max-w-6xl mx-auto px-5 pt-3">
          <div className="flex items-center justify-between gap-3 rounded-lg border border-[#B563FA]/40 bg-[#B563FA]/10 text-[#B563FA] text-sm px-3 py-2">
            <span>{notice}</span>
            <button onClick={() => setNotice("")} className="text-[#B563FA] hover:text-[#F3EEFB]"><X size={14} /></button>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto px-5 py-6">
        {tab === "dashboard" && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              <Card label="Employees" value={summary?.totalEmployees} icon={Users} tint="text-fuchsia-300" loading={dashboardLoading} />
              <Card label="Total Seats" value={summary?.totalSeats} icon={MapPin} tint="text-[#B563FA]" loading={dashboardLoading} />
              <Card label="Occupied" value={summary?.occupied} icon={CheckCircle2} tint="text-amber-300" loading={dashboardLoading} />
              <Card label="Available" value={summary?.available} icon={LayoutGrid} tint="text-emerald-300" loading={dashboardLoading} />
              <Card label="Reserved" value={summary?.reserved} icon={AlertTriangle} tint="text-sky-300" loading={dashboardLoading} />
              <Card label="Pending Joiners" value={summary?.pending} icon={Clock} tint="text-rose-300" loading={dashboardLoading} />
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="rounded-lg border border-[#2E1F47] bg-[#000000] p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#A99BC4] font-mono mb-3">Project-wise Allocation</div>
                <div className="space-y-2.5">
                  {projectUtilization.map((p) => {
                    const pct = p.empCount ? Math.round((p.seatCount / p.empCount) * 100) : 0;
                    return (
                      <div key={p.id}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#F3EEFB]">{p.name}</span>
                          <span className="font-mono text-[#A99BC4]">{p.seatCount}/{p.empCount} seated</span>
                        </div>
                        <div className="h-1.5 bg-[#241934] rounded-full overflow-hidden">
                          <div className="h-full bg-[#B563FA]" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-lg border border-[#2E1F47] bg-[#000000] p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#A99BC4] font-mono mb-3">Floor-wise Occupancy</div>
                <div className="space-y-2.5">
                  {floorUtilization.map((f) => (
                    <div key={f.floor}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#F3EEFB]">Floor {f.floor}</span>
                        <span className="font-mono text-[#A99BC4]">{f.occupied}/{f.total} · {f.pct}%</span>
                      </div>
                      <div className="h-1.5 bg-[#241934] rounded-full overflow-hidden">
                        <div className="h-full bg-amber-400" style={{ width: `${f.pct}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === "employees" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="flex-1 flex items-center gap-2 bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2">
                {employeesLoading ? <Loader2 size={15} className="text-[#A99BC4] animate-spin" /> : <Search size={15} className="text-[#A99BC4]" />}
                <input
                  value={empQuery}
                  onChange={(e) => { setEmpQuery(e.target.value); setPage(0); }}
                  placeholder="Search by name, ID, email, project…"
                  className="bg-transparent outline-none text-sm w-full placeholder:text-[#7A6B96]"
                />
              </div>
              <select
                value={empStatusFilter}
                onChange={(e) => { setEmpStatusFilter(e.target.value); setPage(0); }}
                className="bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm"
              >
                <option>All</option>
                <option>Allocated</option>
                <option>Pending</option>
              </select>
              <button
                onClick={openAddModal}
                className="text-sm font-mono px-3 py-2 rounded-lg border border-[#B563FA]/40 text-[#B563FA] hover:bg-[#B563FA]/10 inline-flex items-center gap-1.5 whitespace-nowrap"
              >
                <Plus size={15} /> Add Employee
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={csvBusy}
                className="text-sm font-mono px-3 py-2 rounded-lg border border-[#2E1F47] text-[#A99BC4] hover:text-[#F3EEFB] hover:border-[#B563FA]/50 inline-flex items-center gap-1.5 whitespace-nowrap disabled:opacity-50"
              >
                {csvBusy ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />} Import CSV
              </button>
              <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleCsvSelected} />
            </div>

            {csvMessage && (
              <div className="text-xs font-mono text-[#A99BC4] border border-[#2E1F47] rounded px-3 py-2">{csvMessage}</div>
            )}

            <div className="rounded-lg border border-[#2E1F47] overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-[#000000] text-[#A99BC4] text-[11px] uppercase tracking-wide font-mono">
                  <tr>
                    <th className="text-left px-3 py-2">Employee</th>
                    <th className="text-left px-3 py-2 hidden lg:table-cell">Department / Role</th>
                    <th className="text-left px-3 py-2 hidden md:table-cell">Project</th>
                    <th className="text-left px-3 py-2 hidden sm:table-cell">Seat</th>
                    <th className="text-left px-3 py-2">Status</th>
                    <th className="text-right px-3 py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((e) => {
                    const seat = e.seat;
                    return (
                      <tr key={e.id} className="border-t border-[#241934] hover:bg-[#000000]/60">
                        <td className="px-3 py-2">
                          <div className="font-medium flex items-center gap-1.5">
                            {e.name}
                            {e.status !== "Active" && <StatusBadge status="Inactive" />}
                          </div>
                          <div className="text-[11px] text-[#A99BC4] font-mono">{e.code} · {e.email}</div>
                        </td>
                        <td className="px-3 py-2 hidden lg:table-cell text-[#D9CCEE] text-xs">
                          {e.department}<div className="text-[11px] text-[#A99BC4]">{e.role} · joined {e.joiningDate}</div>
                        </td>
                        <td className="px-3 py-2 hidden md:table-cell text-[#D9CCEE]">{projectById[e.projectId]?.name}</td>
                        <td className="px-3 py-2 hidden sm:table-cell font-mono text-[#D9CCEE]">
                          {seat ? `F${seat.floor}-${seat.seatNumber}` : "—"}
                        </td>
                        <td className="px-3 py-2"><StatusBadge status={seat ? "Occupied" : "Pending"} /></td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex justify-end flex-wrap gap-1">
                            {seat ? (
                              <button onClick={() => releaseSeat(e.id)} className="text-[11px] font-mono px-2 py-1 rounded border border-[#2E1F47] hover:border-rose-400/50 hover:text-rose-300 inline-flex items-center gap-1">
                                <X size={12} /> Release
                              </button>
                            ) : (
                              <button onClick={() => allocateSeat(e.id)} className="text-[11px] font-mono px-2 py-1 rounded border border-[#2E1F47] hover:border-emerald-400/50 hover:text-emerald-300 inline-flex items-center gap-1">
                                <UserPlus size={12} /> Allocate
                              </button>
                            )}
                            <button onClick={() => openEditModal(e)} className="text-[11px] font-mono px-2 py-1 rounded border border-[#2E1F47] hover:border-[#B563FA]/50 hover:text-[#B563FA] inline-flex items-center gap-1">
                              <Pencil size={12} /> Edit
                            </button>
                            <button onClick={() => deactivateEmployee(e)} className="text-[11px] font-mono px-2 py-1 rounded border border-[#2E1F47] hover:border-rose-400/50 hover:text-rose-300 inline-flex items-center gap-1">
                              <Ban size={12} /> Deactivate
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {!employees.length && !employeesLoading && (
                    <tr><td colSpan={6} className="px-3 py-8 text-center text-[#A99BC4] text-sm">No employees match this search.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between text-xs text-[#A99BC4] font-mono">
              <span>{employeeTotal} result{employeeTotal === 1 ? "" : "s"}</span>
              <div className="flex items-center gap-2">
                <button disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="px-2 py-1 border border-[#2E1F47] rounded disabled:opacity-30">Prev</button>
                <span>Page {page + 1} / {totalPages}</span>
                <button disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)} className="px-2 py-1 border border-[#2E1F47] rounded disabled:opacity-30">Next</button>
              </div>
            </div>
          </div>
        )}

        {tab === "seats" && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2 items-center">
              <select value={seatFloorFilter} onChange={(e) => setSeatFloorFilter(e.target.value)} className="bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                <option value="All">All Floors</option>
                {FLOORS.map((f) => <option key={f} value={f}>Floor {f}</option>)}
              </select>
              <select value={seatZoneFilter} onChange={(e) => setSeatZoneFilter(e.target.value)} className="bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                <option value="All">All Zones</option>
                {ZONES.map((z) => <option key={z} value={z}>Zone {z}</option>)}
              </select>
              <select value={seatStatusFilter} onChange={(e) => setSeatStatusFilter(e.target.value)} className="bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                <option value="All">All Statuses</option>
                {Object.values(STATUS).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              {seatsLoading && <Loader2 size={15} className="text-[#A99BC4] animate-spin" />}
              <div className="ml-auto flex items-center gap-3 text-[11px] font-mono text-[#A99BC4]">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-emerald-400/60 inline-block" /> Available</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-amber-400/60 inline-block" /> Occupied</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-sky-400/60 inline-block" /> Reserved</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-rose-400/60 inline-block" /> Maintenance</span>
              </div>
            </div>
            <div className="text-[11px] font-mono text-[#7A6B96]">
              Showing {seatFloorFilter === "All" ? "all floors" : `Floor ${seatFloorFilter}`} — 5,600 seats total across 5 floors. Narrow by floor/zone for a lighter view.
            </div>

            <div className="rounded-lg border border-[#2E1F47] bg-[#000000] p-4" style={{ backgroundImage: "linear-gradient(#1A1228 1px, transparent 1px), linear-gradient(90deg, #1A1228 1px, transparent 1px)", backgroundSize: "24px 24px" }}>
              <div className="grid gap-1.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(58px, 1fr))" }}>
                {seats.map((s) => {
                  const colors = {
                    [STATUS.AVAILABLE]: "bg-emerald-400/15 border-emerald-400/40 text-emerald-300",
                    [STATUS.OCCUPIED]: "bg-amber-400/15 border-amber-400/40 text-amber-300",
                    [STATUS.RESERVED]: "bg-sky-400/15 border-sky-400/40 text-sky-300",
                    [STATUS.MAINTENANCE]: "bg-rose-400/15 border-rose-400/40 text-rose-300",
                  };
                  const tooltip = s.employeeName
                    ? `${s.status} · ${s.employeeName} · ${projectById[s.projectId]?.name || "—"} · allocated ${s.allocationDate}`
                    : s.status;
                  return (
                    <div
                      key={s.id}
                      title={tooltip}
                      className={`border rounded px-1.5 py-1.5 text-center font-mono text-[10px] leading-tight cursor-default ${colors[s.status]}`}
                    >
                      {s.seatNumber}
                    </div>
                  );
                })}
                {!seats.length && !seatsLoading && <div className="col-span-full text-center text-[#A99BC4] text-sm py-8">No seats match this filter.</div>}
              </div>
            </div>
            <div className="text-xs text-[#A99BC4] font-mono">{seats.length} seats shown</div>
          </div>
        )}

        {tab === "projects" && (
          <div className="grid sm:grid-cols-2 gap-3">
            {projectUtilization.map((p) => (
              <div key={p.id} className="rounded-lg border border-[#2E1F47] bg-[#000000] p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="font-semibold">{p.name}</div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-emerald-400/30 text-emerald-300">{p.status}</span>
                </div>
                <div className="text-xs text-[#A99BC4] mb-3">Manager: {p.manager}</div>
                <div className="flex gap-4 text-sm font-mono">
                  <div><span className="text-[#A99BC4] text-[11px] block">Employees</span>{p.empCount}</div>
                  <div><span className="text-[#A99BC4] text-[11px] block">Occupied Seats</span>{p.seatCount}</div>
                  <div><span className="text-[#A99BC4] text-[11px] block">Pending</span>{p.empCount - p.seatCount}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "ai" && (
          <div className="rounded-lg border border-[#2E1F47] bg-[#000000] flex flex-col h-[65vh]">
            <div className="px-4 py-3 border-b border-[#241934] text-[11px] uppercase tracking-widest text-[#A99BC4] font-mono flex items-center gap-2">
              <MessageSquare size={14} className="text-[#B563FA]" /> Seat &amp; Project Assistant (backend-powered)
            </div>
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {aiLog.map((m, i) => (
                <div key={i} className={`max-w-[85%] ${m.role === "user" ? "ml-auto text-right" : ""}`}>
                  <div className={`inline-block px-3 py-2 rounded-lg text-sm ${
                    m.role === "user" ? "bg-[#B563FA]/15 border border-[#B563FA]/30" :
                    m.role === "system" ? "bg-transparent text-[#A99BC4] text-xs italic" :
                    "bg-[#000000] border border-[#2E1F47]"
                  }`}>
                    {m.text}
                  </div>
                </div>
              ))}
              {aiBusy && (
                <div className="max-w-[85%]">
                  <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm bg-[#000000] border border-[#2E1F47] text-[#A99BC4]">
                    <Loader2 size={13} className="animate-spin" /> thinking…
                  </div>
                </div>
              )}
            </div>
            <div className="p-3 border-t border-[#241934] flex flex-wrap gap-1.5">
              {["Where is Amit seated?", "Available seats on floor 3", "How many seats occupied for project Indigo?", "Who is sitting near Priya?"].map((ex) => (
                <button key={ex} onClick={() => setAiInput(ex)} className="text-[11px] font-mono px-2 py-1 rounded border border-[#2E1F47] text-[#A99BC4] hover:text-[#F3EEFB] hover:border-[#B563FA]/50">
                  {ex}
                </button>
              ))}
            </div>
            <form onSubmit={submitAiQuery} className="p-3 pt-0 flex gap-2">
              <input
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                placeholder="Ask about a seat, project, or availability…"
                className="flex-1 bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#B563FA]/50"
              />
              <button type="submit" disabled={aiBusy} className="px-3 py-2 rounded-lg bg-[#B563FA]/15 border border-[#B563FA]/40 text-[#B563FA] hover:bg-[#B563FA]/25 disabled:opacity-50">
                <Send size={15} />
              </button>
            </form>
          </div>
        )}
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="w-full max-w-md rounded-lg border border-[#2E1F47] bg-[#0A0710] p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-semibold text-[#B563FA]">Add New Joiner</div>
              <button onClick={() => setShowAddModal(false)} className="text-[#A99BC4] hover:text-[#F3EEFB]"><X size={16} /></button>
            </div>
            <form onSubmit={submitAddEmployee} className="space-y-3">
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Name</label>
                <input required value={addForm.name} onChange={(e) => setAddForm((f) => ({ ...f, name: e.target.value }))}
                  className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#B563FA]/50" />
              </div>
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Email</label>
                <input required type="email" value={addForm.email} onChange={(e) => setAddForm((f) => ({ ...f, email: e.target.value }))}
                  className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#B563FA]/50" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Department</label>
                  <select value={addForm.department} onChange={(e) => setAddForm((f) => ({ ...f, department: e.target.value }))}
                    className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                    {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Role</label>
                  <select value={addForm.role} onChange={(e) => setAddForm((f) => ({ ...f, role: e.target.value }))}
                    className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Joining Date</label>
                  <input type="date" value={addForm.joiningDate} onChange={(e) => setAddForm((f) => ({ ...f, joiningDate: e.target.value }))}
                    className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Project</label>
                  <select value={addForm.projectId} onChange={(e) => setAddForm((f) => ({ ...f, projectId: e.target.value }))}
                    className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                    <option value="">Unassigned</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              </div>
              <label className="flex items-center gap-2 text-xs text-[#A99BC4] font-mono">
                <input type="checkbox" checked={addForm.autoAllocate} onChange={(e) => setAddForm((f) => ({ ...f, autoAllocate: e.target.checked }))} />
                Auto-allocate a seat on creation
              </label>
              {addError && <div className="text-xs text-rose-300 border border-rose-400/30 bg-rose-400/10 rounded px-2 py-1.5">{addError}</div>}
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => setShowAddModal(false)} className="text-sm px-3 py-1.5 rounded-lg border border-[#2E1F47] text-[#A99BC4] hover:text-[#F3EEFB]">Cancel</button>
                <button type="submit" disabled={addSubmitting} className="text-sm px-3 py-1.5 rounded-lg bg-[#B563FA]/15 border border-[#B563FA]/40 text-[#B563FA] hover:bg-[#B563FA]/25 inline-flex items-center gap-1.5 disabled:opacity-50">
                  {addSubmitting && <Loader2 size={13} className="animate-spin" />} Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingEmployee && editForm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="w-full max-w-md rounded-lg border border-[#2E1F47] bg-[#0A0710] p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-sm font-semibold text-[#B563FA]">Edit Employee</div>
                <div className="text-[11px] font-mono text-[#A99BC4]">{editingEmployee.code}</div>
              </div>
              <button onClick={() => setEditingEmployee(null)} className="text-[#A99BC4] hover:text-[#F3EEFB]"><X size={16} /></button>
            </div>
            <form onSubmit={submitEditEmployee} className="space-y-3">
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Name</label>
                <input required value={editForm.name} onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                  className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#B563FA]/50" />
              </div>
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Email</label>
                <input required type="email" value={editForm.email} onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))}
                  className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#B563FA]/50" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Department</label>
                  <select value={editForm.department} onChange={(e) => setEditForm((f) => ({ ...f, department: e.target.value }))}
                    className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                    {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Role</label>
                  <select value={editForm.role} onChange={(e) => setEditForm((f) => ({ ...f, role: e.target.value }))}
                    className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Joining Date</label>
                  <input type="date" value={editForm.joiningDate} onChange={(e) => setEditForm((f) => ({ ...f, joiningDate: e.target.value }))}
                    className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Project</label>
                  <select value={editForm.projectId} onChange={(e) => setEditForm((f) => ({ ...f, projectId: e.target.value }))}
                    className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                    <option value="">Unassigned</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Employment Status</label>
                <select value={editForm.status} onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value }))}
                  className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm">
                  <option>Active</option>
                  <option>Inactive</option>
                </select>
              </div>
              {editError && <div className="text-xs text-rose-300 border border-rose-400/30 bg-rose-400/10 rounded px-2 py-1.5">{editError}</div>}
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => setEditingEmployee(null)} className="text-sm px-3 py-1.5 rounded-lg border border-[#2E1F47] text-[#A99BC4] hover:text-[#F3EEFB]">Cancel</button>
                <button type="submit" disabled={editSubmitting} className="text-sm px-3 py-1.5 rounded-lg bg-[#B563FA]/15 border border-[#B563FA]/40 text-[#B563FA] hover:bg-[#B563FA]/25 inline-flex items-center gap-1.5 disabled:opacity-50">
                  {editSubmitting && <Loader2 size={13} className="animate-spin" />} Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
