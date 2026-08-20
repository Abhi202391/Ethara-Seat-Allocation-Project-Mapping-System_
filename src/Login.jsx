import React, { useState } from "react";
import { Loader2, Lock } from "lucide-react";
import { api } from "./api";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const session = await api.login(email, password);
      onLogin(session);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function fillDemo(role) {
    if (role === "manager") {
      setEmail("manager@ethara.ai");
      setPassword("Manager@123");
    } else {
      setEmail("employee@ethara.ai");
      setPassword("Employee@123");
    }
  }

  return (
    <div className="min-h-screen bg-[#000000] text-[#F3EEFB] font-sans flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <div className="text-[11px] font-mono tracking-[0.25em] text-[#B563FA] uppercase">Ethara · Facilities</div>
          <h1 className="text-lg font-semibold tracking-tight text-[#B563FA] mt-1">Sign in</h1>
        </div>

        <form onSubmit={submit} className="rounded-lg border border-[#2E1F47] bg-[#0A0710] p-5 space-y-3">
          <div>
            <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Email</label>
            <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#B563FA]/50" />
          </div>
          <div>
            <label className="text-[11px] font-mono uppercase tracking-wide text-[#A99BC4]">Password</label>
            <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full bg-[#000000] border border-[#2E1F47] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#B563FA]/50" />
          </div>
          {error && <div className="text-xs text-rose-300 border border-rose-400/30 bg-rose-400/10 rounded px-2 py-1.5">{error}</div>}
          <button type="submit" disabled={busy} className="w-full text-sm px-3 py-2 rounded-lg bg-[#B563FA]/15 border border-[#B563FA]/40 text-[#B563FA] hover:bg-[#B563FA]/25 inline-flex items-center justify-center gap-1.5 disabled:opacity-50">
            {busy && <Loader2 size={14} className="animate-spin" />} <Lock size={13} /> Sign in
          </button>
        </form>

        <div className="mt-4 rounded-lg border border-[#2E1F47] bg-[#0A0710] p-3 text-[11px] font-mono text-[#A99BC4] space-y-2">
          <div className="uppercase tracking-wide text-[#7A6B96]">Demo accounts</div>
          <button type="button" onClick={() => fillDemo("manager")} className="w-full text-left flex items-center justify-between px-2 py-1.5 rounded border border-[#2E1F47] hover:border-[#B563FA]/50 hover:text-[#F3EEFB]">
            <span>Manager — full access</span>
            <span className="text-[#7A6B96]">use →</span>
          </button>
          <button type="button" onClick={() => fillDemo("employee")} className="w-full text-left flex items-center justify-between px-2 py-1.5 rounded border border-[#2E1F47] hover:border-[#B563FA]/50 hover:text-[#F3EEFB]">
            <span>Employee — read-only</span>
            <span className="text-[#7A6B96]">use →</span>
          </button>
        </div>
      </div>
    </div>
  );
}
