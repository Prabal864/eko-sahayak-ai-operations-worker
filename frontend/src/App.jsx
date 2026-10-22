import { useEffect, useMemo, useState } from "react";

const api = async (path, options) => {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error((await response.json()).detail || "Request failed");
  return response.json();
};

const initials = (name) => name.split(" ").map((part) => part[0]).slice(0, 2).join("");
const formatDate = (date) => new Date(date).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" });
const formatEvent = (event) => event.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());

function Badge({ value }) {
  return <span className={`badge ${value}`}>{value.replace("_", " ")}</span>;
}

function Navigation({ view, setView }) {
  return <aside className="sidebar">
    <div className="brand"><div className="brand-mark">e</div><div><strong>Eko Sahayak</strong><span>Operations worker</span></div></div>
    <nav aria-label="Main navigation">
      {[["overview", "▦", "Operations desk"], ["new-case", "＋", "New case"], ["audit", "◷", "Audit trail"]].map(([key, icon, label]) =>
        <button key={key} className={`nav-item ${view === key ? "active" : ""}`} onClick={() => setView(key)}><span>{icon}</span>{label}</button>)}
    </nav>
    <div className="sidebar-bottom">
      <div className="privacy-mini"><span className="dot" /><div><b>Local-first mode</b><small>PII stays on device</small></div></div>
      <div className="profile"><div className="avatar">PG</div><div><b>Prabal Goswami</b><small>Field operations</small></div><span>•••</span></div>
    </div>
  </aside>;
}

function Header({ label }) {
  return <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <b>{label}</b></div><div className="top-actions"><button className="icon-btn" title="Notifications">♧<i /></button><button className="help-btn">?</button></div></header>;
}

function Overview({ cases, summary, onNew, onOpen }) {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const filtered = useMemo(() => cases.filter((item) => {
    const inFilter = filter === "all" || item.status === filter || item.priority === filter;
    return inFilter && JSON.stringify(item).toLowerCase().includes(search.toLowerCase());
  }), [cases, filter, search]);
  return <div className="page">
    <div className="page-head"><div><h1>Good morning, Prabal</h1><p>Here’s what needs your attention across today’s field operations.</p></div><button className="primary" onClick={onNew}>＋ Log a new case</button></div>
    <div className="metrics">
      <Metric label="Open cases" value={summary.open} change="↑ 12% this week" icon="◔" />
      <Metric label="Needs escalation" value={summary.urgent} change="2 awaiting owner" icon="!" tone="orange" />
      <Metric label="Resolved this week" value={summary.resolved} change="↑ 8% this week" icon="✓" tone="green" />
    </div>
    <div className="section-head"><h2>Case queue</h2><button onClick={() => window.alert("Every case follows: capture → triage → act → verify → close.")}>View workflow guide →</button></div>
    <div className="table-wrap"><div className="filters"><div className="filter-tabs">{["all", "in_review", "urgent", "resolved"].map((item) => <button className={filter === item ? "active" : ""} onClick={() => setFilter(item)} key={item}>{item === "all" ? "All cases" : item === "in_review" ? "In review" : item[0].toUpperCase() + item.slice(1)}</button>)}</div><input className="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search cases..." aria-label="Search cases" /></div>
      <table><thead><tr><th>Case</th><th>Issue & root cause</th><th>Priority</th><th>Owner</th><th>Status</th><th /></tr></thead><tbody>{filtered.length ? filtered.map((item) => <tr key={item.id}><td><span className="case-id">{item.id}</span><span className="case-sub">{formatDate(item.created_at)}</span></td><td><span className="case-type">{item.category}</span><span className="case-sub">{item.root_cause}</span></td><td><Badge value={item.priority} /></td><td><div className="owner"><span className="owner-dot">{initials(item.owner)}</span>{item.owner}</div></td><td><Badge value={item.status} /></td><td><button className="action-link" onClick={() => onOpen(item.id)}>Open case →</button></td></tr>) : <tr><td colSpan="6" className="empty">No cases in this view.</td></tr>}</tbody></table>
    </div>
  </div>;
}

function Metric({ label, value, change, icon, tone = "blue" }) {
  return <div className="metric"><span className="metric-label">{label}</span><div className="metric-row"><strong>{value}</strong><span className={`metric-change ${tone}`}>{change}</span><span className={`metric-icon ${tone}`}>{icon}</span></div></div>;
}

function NewCase({ onCreated }) {
  const [summary, setSummary] = useState("");
  const [source, setSource] = useState("voice_note");
  const [language, setLanguage] = useState("English");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    if (summary.trim().length < 8) return;
    setBusy(true);
    try { const result = await api("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ summary, source, language, consent_to_share: consent }) }); onCreated(result); }
    catch (error) { window.alert(error.message); } finally { setBusy(false); }
  };
  return <div className="page"><div className="page-head"><div><h1>Log a new case</h1><p>Capture the situation in the entrepreneur’s own words. Sahayak will structure the next safe action.</p></div></div>
    <div className="form-grid"><form className="form-panel" onSubmit={submit}><h2>What happened?</h2><p>Keep it short and factual. Do not include OTPs, PINs, full account numbers, or unnecessary identity details.</p><div className="field"><label htmlFor="summary">Field note or support issue</label><textarea id="summary" value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Example: Ramesh says money was debited but the retailer settlement has not arrived since yesterday..." /></div><div className="field"><label>Input source</label><div className="source-row">{["voice_note", "support", "field_visit", "activity_log"].map((item) => <button type="button" className={`source ${source === item ? "selected" : ""}`} onClick={() => setSource(item)} key={item}>{item.replace("_", " ")}</button>)}</div></div><div className="field"><label htmlFor="language">Preferred language</label><select id="language" value={language} onChange={(event) => setLanguage(event.target.value)}><option>English</option><option>Hindi</option><option>Hinglish</option></select></div><label className="consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> I have explicit consent to share a non-identifying summary with Eko for operational follow-up.</label><button className="primary" disabled={busy}>{busy ? "Structuring note…" : "Analyze & create case"}</button></form>
      <aside className="form-panel"><h2>Privacy guardrails</h2><p>Designed for a shared phone or low-end laptop in a real field setting.</p><div className="privacy-note">✓ Raw notes stay local in this demo<br />✓ Analysis uses explainable rules<br />✓ Share only a redacted summary with consent<br />✓ Human review for money movement and safety</div><div className="result-block"><label>Workflow states</label><p>New → In review → Resolved<br />                     ↘ Escalated</p></div><div className="result-block"><label>Definition of done</label><p>A clear owner, next action, evidence trail, and a human handoff when confidence or risk is low.</p></div></aside>
    </div></div>;
}

function CaseDetail({ item, onBack, onUpdated }) {
  const [status, setStatus] = useState(item.status);
  const save = async () => { const updated = await api(`/api/cases/${item.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }); onUpdated(updated); };
  return <div className="page"><div className="page-head"><div><button className="action-link" onClick={onBack}>← Back to case queue</button><h1 style={{ marginTop: 12 }}>{item.category}</h1><p>{item.id} · Created {formatDate(item.created_at)}</p></div><div><Badge value={item.priority} /> <Badge value={item.status} /></div></div><div className="form-grid"><section className="form-panel"><div className="result-head"><h2>Resolution brief</h2><span className="confidence">{Math.round(item.confidence * 100)}% confidence</span></div><p className="result-summary">{item.root_cause}</p><ResultBlock label="Recommended next action">{item.next_action}</ResultBlock><div className="result-grid"><ResultBlock label="Likely owner">{item.owner}</ResultBlock><ResultBlock label="Escalation path">{item.escalation}</ResultBlock></div><div className="result-block"><label>Evidence used</label>{item.evidence.map((evidence) => <p key={evidence}>• {evidence}</p>)}</div><div className="privacy-note">Privacy check: {item.consent_to_share ? "Consent recorded for a non-identifying summary." : "No sharing consent recorded. Keep this case local."}</div></section><aside className="form-panel"><h2>Move workflow forward</h2><p>Autonomous recommendations stop here. A human owns the decision to close or escalate.</p><div className="field"><label htmlFor="status">Update case status</label><select id="status" value={status} onChange={(event) => setStatus(event.target.value)}><option value="in_review">in review</option><option value="resolved">resolved</option><option value="escalated">escalated</option></select></div><button className="primary" onClick={save}>Save status</button><div className="result-block"><label>Audit events</label>{item.audit.map((event) => <p key={`${event.event}-${event.at}`}><b>{formatEvent(event.event)}</b><br /><span className="muted">{event.detail}</span></p>)}</div></aside></div></div>;
}

function ResultBlock({ label, children }) { return <div className="result-block"><label>{label}</label><p>{children}</p></div>; }

function Audit() {
  const [events, setEvents] = useState([]);
  useEffect(() => { api("/api/audit").then((data) => setEvents(data.events.reverse())); }, []);
  return <div className="page"><div className="page-head"><div><h1>Audit trail</h1><p>Every recommendation and handoff is traceable without exporting raw personal data.</p></div></div><div className="audit-list">{events.map((event) => <div className="audit-row" key={`${event.case_id}-${event.at}`}><span className="audit-dot" /><div><b>{formatEvent(event.event)}</b><small>{event.detail} · {event.case_id} · {formatDate(event.at)}</small></div></div>)}</div></div>;
}

export default function App() {
  const [view, setView] = useState("overview");
  const [cases, setCases] = useState([]);
  const [summary, setSummary] = useState({ open: 0, urgent: 0, resolved: 0 });
  const [selected, setSelected] = useState(null);
  const refresh = () => api("/api/cases").then((data) => { setCases(data.cases); setSummary(data.summary); return data; });
  useEffect(() => { refresh(); }, []);
  const openCase = (id) => { setSelected(cases.find((item) => item.id === id)); setView("case"); };
  const content = view === "overview" ? <Overview cases={cases} summary={summary} onNew={() => setView("new-case")} onOpen={openCase} /> : view === "new-case" ? <NewCase onCreated={(item) => { setCases((current) => [item, ...current]); setSelected(item); setView("case"); }} /> : view === "audit" ? <Audit /> : selected ? <CaseDetail item={selected} onBack={() => setView("overview")} onUpdated={(updated) => { setCases((current) => current.map((item) => item.id === updated.id ? updated : item)); setSelected(updated); }} /> : null;
  const label = view === "case" && selected ? selected.id : view === "new-case" ? "New case" : view === "audit" ? "Audit trail" : "Operations desk";
  return <><Navigation view={view} setView={setView} /><main className="main"><Header label={label} />{content}</main></>;
}
