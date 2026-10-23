import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  || (import.meta.env.DEV ? "" : "https://api.prabalsingh.dev");

const api = async (path, options = {}) => {
  const token = localStorage.getItem("eko_session");
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.detail || "Request failed");
    error.status = response.status;
    throw error;
  }
  return response.json();
};

const initials = (name) => name.split(" ").map((part) => part[0]).slice(0, 2).join("");
const formatDate = (date) => new Date(date).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" });
const formatEvent = (event) => event.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());

function Badge({ value }) {
  return <span className={`badge ${value}`}>{value.replace("_", " ")}</span>;
}

function Navigation({ view, setView, user, onLogout }) {
  return <aside className="sidebar">
    <div className="brand"><div className="brand-mark">e</div><div><strong>Eko Sahayak</strong><span>Operations worker</span></div></div>
    <nav aria-label="Main navigation">
      {[["overview", "▦", "Operations desk"], ["new-case", "＋", "New case"], ["audit", "◷", "Audit trail"]].map(([key, icon, label]) =>
        <button key={key} className={`nav-item ${view === key ? "active" : ""}`} onClick={() => setView(key)}><span>{icon}</span>{label}</button>)}
    </nav>
    <div className="sidebar-bottom">
      <div className="privacy-mini"><span className="dot" /><div><b>Local-first mode</b><small>PII stays on device</small></div></div>
      <div className="profile"><div className="avatar">{initials(user.name)}</div><div><b>{user.name}</b><small>{user.role}</small></div><button className="logout-link" onClick={onLogout}>Log out</button></div>
    </div>
  </aside>;
}

function Header({ label, user, onLogout }) {
  return <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <b>{label}</b></div><div className="top-actions"><span className="signed-in">Signed in as {user.username}</span><button className="icon-btn" title="Notifications">♧<i /></button><button className="help-btn">?</button><button className="header-logout" onClick={onLogout}>Log out</button></div></header>;
}

function Login({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    if (mode === "signup" && password !== confirmPassword) {
      setError("Passwords do not match.");
      setBusy(false);
      return;
    }
    try {
      const path = mode === "login" ? "/eko/auth/login" : "/eko/auth/signup";
      const body = mode === "login" ? { username, password } : { name, username, password };
      const result = await api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      localStorage.setItem("eko_session", result.token);
      onLogin(result.user);
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setBusy(false);
    }
  };
  return <main className="login-shell"><section className="login-panel"><div className="login-brand"><div className="brand-mark">e</div><div><strong>Eko Sahayak</strong><span>Operations worker</span></div></div><h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1><p>{mode === "login" ? "Sign in to review field operations and resolve cases safely." : "Create a local operator account to access the operations desk."}</p><form onSubmit={submit}>{mode === "signup" && <div className="field"><label htmlFor="name">Full name</label><input id="name" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Enter your name" required /></div>}<div className="field"><label htmlFor="username">Username</label><input id="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Enter username" required /></div><div className="field"><label htmlFor="password">Password</label><input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={mode === "login" ? "Enter password" : "At least 8 characters"} required /></div>{mode === "signup" && <div className="field"><label htmlFor="confirm-password">Confirm password</label><input id="confirm-password" type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Re-enter password" required /></div>}{error && <div className="form-error" role="alert">{error}</div>}<button className="primary login-button" disabled={busy}>{busy ? (mode === "login" ? "Signing in…" : "Creating account…") : (mode === "login" ? "Sign in" : "Create account")}</button></form><button className="auth-switch" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}> {mode === "login" ? "Need an account? Sign up" : "Already have an account? Sign in"}</button><div className="login-note"><span className="dot" /><span>Local demo access. Your session is kept on this device.</span></div></section></main>;
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
  const [recording, setRecording] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("");
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const recognitionRef = useRef(null);
  const browserTranscriptRef = useRef(false);
  const startVoice = async () => {
    setVoiceStatus("");
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = language === "Hindi" ? "hi-IN" : "en-IN";
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        browserTranscriptRef.current = true;
        setSummary((current) => current ? `${current} ${transcript}` : transcript);
        setVoiceStatus("Transcript added from browser speech recognition.");
      };
      recognition.onerror = () => setVoiceStatus("Browser transcription was unavailable; the audio recording was kept for server transcription.");
      recognitionRef.current = recognition;
      recognition.start();
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      if (!SpeechRecognition) setVoiceStatus("This browser does not support microphone recording. Type the note instead.");
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setVoiceStatus("Microphone permission was not granted. You can type the note instead.");
      return;
    }
    const recorder = new MediaRecorder(stream);
    browserTranscriptRef.current = false;
    chunksRef.current = [];
    recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
    recorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      if (browserTranscriptRef.current) return;
      if (!consent) {
        setVoiceStatus("Audio stayed on this device because sharing consent is disabled.");
        return;
      }
      const form = new FormData();
      form.append("audio", blob, "voice-note.webm");
      try {
        const result = await api("/eko/voice/transcribe", { method: "POST", body: form });
        setSummary((current) => current ? `${current} ${result.transcript}` : result.transcript);
        setVoiceStatus("Server transcription added.");
      } catch (error) {
        if (!recognitionRef.current) setVoiceStatus(error.message);
      }
    };
    recorderRef.current = recorder;
    recorder.start();
    setRecording(true);
    setVoiceStatus("Listening… speak the operational update, then stop.");
  };
  const stopVoice = () => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    setRecording(false);
  };
  const submit = async (event) => {
    event.preventDefault();
    if (summary.trim().length < 8) return;
    setBusy(true);
    try { const result = await api("/eko/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ summary, source, language, consent_to_share: consent }) }); onCreated(result); }
    catch (error) { window.alert(error.message); } finally { setBusy(false); }
  };
  return <div className="page"><div className="page-head"><div><h1>Log a new case</h1><p>Capture the situation in the entrepreneur’s own words. Sahayak will structure the next safe action.</p></div></div>
    <div className="form-grid"><form className="form-panel" onSubmit={submit}><h2>What happened?</h2><p>Keep it short and factual. Do not include OTPs, PINs, full account numbers, or unnecessary identity details.</p><div className="field"><label htmlFor="summary">Field note or support issue</label><textarea id="summary" value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Example: Ramesh says money was debited but the retailer settlement has not arrived since yesterday..." /><div className="voice-controls"><button type="button" className={`voice-button ${recording ? "recording" : ""}`} onClick={recording ? stopVoice : startVoice}>{recording ? "■ Stop recording" : "● Add voice note"}</button><span className="voice-status">{voiceStatus}</span></div></div><div className="field"><label>Input source</label><div className="source-row">{["voice_note", "support", "field_visit", "activity_log"].map((item) => <button type="button" className={`source ${source === item ? "selected" : ""}`} onClick={() => setSource(item)} key={item}>{item.replace("_", " ")}</button>)}</div></div><div className="field"><label htmlFor="language">Preferred language</label><select id="language" value={language} onChange={(event) => setLanguage(event.target.value)}><option>English</option><option>Hindi</option><option>Hinglish</option></select></div><label className="consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> I have explicit consent to share a non-identifying summary with Eko for operational follow-up.</label><button className="primary" disabled={busy}>{busy ? "Structuring note…" : "Analyze & create case"}</button></form>
      <aside className="form-panel"><h2>Privacy guardrails</h2><p>Designed for a shared phone or low-end laptop in a real field setting.</p><div className="privacy-note">✓ Raw notes stay local in this demo<br />✓ Analysis uses explainable rules<br />✓ Share only a redacted summary with consent<br />✓ Human review for money movement and safety</div><div className="result-block"><label>Workflow states</label><p>New → In review → Resolved<br />                     ↘ Escalated</p></div><div className="result-block"><label>Definition of done</label><p>A clear owner, next action, evidence trail, and a human handoff when confidence or risk is low.</p></div></aside>
    </div></div>;
}

function CaseDetail({ item, onBack, onUpdated, onArchived }) {
  const [status, setStatus] = useState(item.status);
  const save = async () => { const updated = await api(`/eko/cases/${item.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }); onUpdated(updated); };
  const archive = async () => { if (!window.confirm("Archive this case? It will leave the active queue but remain available for audit.")) return; const updated = await api(`/eko/cases/${item.id}/archive`, { method: "POST" }); onArchived(updated.id); };
  return <div className="page"><div className="page-head"><div><button className="action-link" onClick={onBack}>← Back to case queue</button><h1 style={{ marginTop: 12 }}>{item.category}</h1><p>{item.id} · Created {formatDate(item.created_at)}</p></div><div><Badge value={item.priority} /> <Badge value={item.status} /></div></div><div className="form-grid"><section className="form-panel"><div className="result-head"><h2>Resolution brief</h2><span className="confidence">{Math.round(item.confidence * 100)}% confidence</span></div><p className="result-summary">{item.root_cause}</p><ResultBlock label="Recommended next action">{item.next_action}</ResultBlock><div className="result-grid"><ResultBlock label="Likely owner">{item.owner}</ResultBlock><ResultBlock label="Escalation path">{item.escalation}</ResultBlock></div><div className="result-block"><label>Evidence used</label>{item.evidence.map((evidence) => <p key={evidence}>• {evidence}</p>)}</div><div className="privacy-note">Privacy check: {item.consent_to_share ? "Consent recorded for a non-identifying summary." : "No sharing consent recorded. Keep this case local."}</div></section><aside className="form-panel"><h2>Move workflow forward</h2><p>Autonomous recommendations stop here. A human owns the decision to close or escalate.</p><div className="field"><label htmlFor="status">Update case status</label><select id="status" value={status} onChange={(event) => setStatus(event.target.value)}><option value="in_review">in review</option><option value="resolved">resolved</option><option value="escalated">escalated</option></select></div><button className="primary" onClick={save}>Save status</button><button className="action-link" onClick={archive}>Archive case</button><div className="result-block"><label>Audit events</label>{item.audit.map((event) => <p key={`${event.event}-${event.at}`}><b>{formatEvent(event.event)}</b><br /><span className="muted">{event.detail}</span></p>)}</div></aside></div></div>;
}

function ResultBlock({ label, children }) { return <div className="result-block"><label>{label}</label><p>{children}</p></div>; }

function Audit() {
  const [events, setEvents] = useState([]);
  useEffect(() => { api("/eko/audit").then((data) => setEvents(data.events.reverse())); }, []);
  return <div className="page"><div className="page-head"><div><h1>Audit trail</h1><p>Every recommendation and handoff is traceable without exporting raw personal data.</p></div></div><div className="audit-list">{events.map((event) => <div className="audit-row" key={`${event.case_id}-${event.at}`}><span className="audit-dot" /><div><b>{formatEvent(event.event)}</b><small>{event.detail} · {event.case_id} · {formatDate(event.at)}</small></div></div>)}</div></div>;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [view, setView] = useState("overview");
  const [cases, setCases] = useState([]);
  const [summary, setSummary] = useState({ open: 0, urgent: 0, resolved: 0 });
  const [selected, setSelected] = useState(null);
  const refresh = () => api("/eko/cases").then((data) => { setCases(data.cases); setSummary(data.summary); return data; });
  useEffect(() => {
    const token = localStorage.getItem("eko_session");
    if (!token) { setAuthChecked(true); return; }
    api("/eko/auth/me").then((data) => setUser(data.user)).catch(() => localStorage.removeItem("eko_session")).finally(() => setAuthChecked(true));
  }, []);
  useEffect(() => {
    if (!user) return;
    refresh().catch((error) => {
      if (error.status === 401) handleLogout();
    });
  }, [user]);
  const handleLogout = async () => {
    try { await api("/eko/auth/logout", { method: "POST" }); } catch { /* Session cleanup still happens locally. */ }
    localStorage.removeItem("eko_session");
    setUser(null);
    setSelected(null);
    setView("overview");
  };
  if (!authChecked) return <main className="auth-loading">Checking your session…</main>;
  if (!user) return <Login onLogin={setUser} />;
  const openCase = (id) => { setSelected(cases.find((item) => item.id === id)); setView("case"); };
  const content = view === "overview" ? <Overview cases={cases} summary={summary} onNew={() => setView("new-case")} onOpen={openCase} /> : view === "new-case" ? <NewCase onCreated={(item) => { setCases((current) => [item, ...current]); setSelected(item); setView("case"); }} /> : view === "audit" ? <Audit /> : selected ? <CaseDetail item={selected} onBack={() => setView("overview")} onUpdated={(updated) => { setCases((current) => current.map((item) => item.id === updated.id ? updated : item)); setSelected(updated); }} onArchived={(id) => { setCases((current) => current.filter((item) => item.id !== id)); setSelected(null); setView("overview"); }} /> : null;
  const label = view === "case" && selected ? selected.id : view === "new-case" ? "New case" : view === "audit" ? "Audit trail" : "Operations desk";
  return <><Navigation view={view} setView={setView} user={user} onLogout={handleLogout} /><main className="main"><Header label={label} user={user} onLogout={handleLogout} />{content}</main></>;
}
