import React, { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  Code2,
  Inbox,
  Layers3,
  LoaderCircle,
  Mail,
  Plus,
  RotateCcw,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  X,
} from "lucide-react";
import "./style.css";

type Mode = "choice" | "noul" | "score" | "combined";
type Routing = {
  team: string;
  priority: string;
  review_required?: boolean;
  reasons?: string[];
  refund?: string;
};
type Answer = {
  choice?: string;
  confidence?: number;
  probabilities?: Record<string, number> | number[];
  noul?: number;
  score?: number;
};
type Result = {
  raw: { answers: Record<string, Answer> };
  elapsed_ms: number;
  policy: Routing | null;
};
type Run = {
  id: string;
  mode: Mode;
  status: string;
  result: Result | null;
  error: string | null;
};
type Ticket = {
  id: string;
  subject: string;
  body: string;
  customer: string;
  preset: string | null;
  routing: Routing | null;
  correction: Routing | null;
  runs: Run[];
};
type Question = {
  type: string;
  instructions: string;
  criteria?: Record<string, string> | string[];
};
type Config = {
  configured: boolean;
  model: string;
  modes: Record<Mode, { questions: Record<string, Question>; python: string }>;
};
const MODES: Mode[] = ["choice", "noul", "score", "combined"];
const names: Record<string, string> = {
  choice: "Choice",
  noul: "Noul",
  score: "Score",
  combined: "Combined",
  billing: "Billing",
  technical: "Technical",
  account: "Account",
  other: "Other",
  standard: "Standard",
  urgent: "Urgent",
  needs_review: "Needs review",
  all: "All tickets",
  unclassified: "Unclassified",
};
const modeCopy: Record<Mode, { title: string; description: string }> = {
  choice: {
    title: "Which team should handle this?",
    description: "Choose one option from a defined set.",
  },
  noul: {
    title: "Is the customer requesting a refund?",
    description: "Measure the probability that a statement is true.",
  },
  score: {
    title: "How much is their work affected?",
    description: "Evaluate impact against an ordered rubric.",
  },
  combined: {
    title: "One ticket. All three types.",
    description:
      "Ask four independent questions, then apply routing rules in Python.",
  },
};
const label = (value: string) => names[value] ?? value;
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
const effective = (ticket: Ticket) => ticket.correction ?? ticket.routing;
const queueOf = (ticket: Ticket) => {
  const route = effective(ticket);
  return !route
    ? "unclassified"
    : route.priority === "needs_review"
      ? "needs_review"
      : route.team;
};
async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Demo-Request": "support-desk",
    },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : `Request failed (${response.status}). Check the fields and try again.`,
    );
  }
  return response.json();
}
function Bars({ values }: { values: [string, number][] }) {
  return (
    <div className="bars">
      {values.map(([name, value]) => (
        <div className="bar-row" key={name}>
          <div className="bar-label">
            <span>{label(name)}</span>
            <strong>{percent(value)}</strong>
          </div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
function AnswerView({
  answer,
  question,
}: {
  answer: Answer;
  question: Question;
}) {
  if (question.type === "Noul") {
    const probability = answer.noul ?? 0;
    return (
      <div className="answer">
        <div className="answer-head">
          <span>{question.instructions.split("?")[0]}?</span>
          <strong>{percent(probability)} true</strong>
        </div>
        <div
          className="binary-meter"
          aria-label={`True ${percent(probability)}, false ${percent(1 - probability)}`}
        >
          <span style={{ width: `${probability * 100}%` }} />
        </div>
        <div className="meter-labels">
          <span>True {percent(probability)}</span>
          <span>False {percent(1 - probability)}</span>
        </div>
        <p className="explanation">
          Noul returns a probability from 0 to 1. It has no separate confidence
          field.
        </p>
      </div>
    );
  }
  const values: [string, number][] =
    question.type === "Score"
      ? (question.criteria as string[]).map((name, index) => [
          `${index} · ${name}`,
          Number(
            Array.isArray(answer.probabilities)
              ? (answer.probabilities[index] ?? 0)
              : (answer.probabilities?.[String(index)] ?? 0),
          ),
        ])
      : Object.entries(answer.probabilities ?? {});
  return (
    <div className="answer">
      <div className="answer-head">
        <span>
          {question.type === "Choice" ? "Suggested team" : "Impact score"}
        </span>
        <strong>
          {question.type === "Choice"
            ? label(answer.choice ?? "")
            : `${answer.score?.toFixed(2)} / 2`}
        </strong>
      </div>
      <Bars values={values} />
      <div className="confidence">
        Confidence <strong>{percent(answer.confidence ?? 0)}</strong>
      </div>
      <p className="explanation">
        {question.type === "Score"
          ? "The score is a weighted average of rubric positions, not a percentage."
          : "Confidence describes this distribution, not a measured chance of being correct."}
      </p>
    </div>
  );
}
export function App() {
  const refreshVersion = useRef(0);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [config, setConfig] = useState<Config | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("combined");
  const [exploring, setExploring] = useState(false);
  const [queue, setQueue] = useState("all");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [compose, setCompose] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const selected = tickets.find((ticket) => ticket.id === selectedId);
  const visible = tickets.filter(
    (ticket) => queue === "all" || queueOf(ticket) === queue,
  );
  const run = selected?.runs.find((item) => item.mode === mode);
  const active =
    selected?.runs.some((item) => item.status === "running") ?? false;
  async function refresh() {
    const version = ++refreshVersion.current;
    const next = await api<Ticket[]>("/tickets");
    if (version === refreshVersion.current) setTickets(next);
    return next;
  }
  async function load() {
    setLoading(true);
    setError("");
    try {
      const [settings, next] = await Promise.all([
        api<Config>("/config"),
        api<Ticket[]>("/tickets"),
      ]);
      setConfig(settings);
      setTickets(next);
      setSelectedId(next[0]?.id ?? null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  useEffect(() => {
    if (
      busy ||
      !tickets.some((ticket) =>
        ticket.runs.some((item) => item.status === "running"),
      )
    )
      return;
    const timer = window.setInterval(() => {
      void refresh().catch((e) => setError(e.message));
    }, 2000);
    return () => {
      window.clearInterval(timer);
      refreshVersion.current++;
    };
  }, [tickets, busy]);
  function choose(ticket: Ticket) {
    setSelectedId(ticket.id);
    setCompose(false);
    setCorrecting(false);
    setError("");
    setNotice("");
  }
  function filter(nextQueue: string) {
    setQueue(nextQueue);
    setCompose(false);
    setCorrecting(false);
    const next = tickets.filter(
      (ticket) => nextQueue === "all" || queueOf(ticket) === nextQueue,
    );
    if (!next.some((ticket) => ticket.id === selectedId))
      setSelectedId(next[0]?.id ?? null);
  }
  async function classify() {
    if (!selected) return;
    refreshVersion.current++;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await api<Ticket>(
        `/tickets/${selected.id}/runs`,
        "POST",
        { mode },
      );
      setTickets((current) =>
        current.map((ticket) => (ticket.id === updated.id ? updated : ticket)),
      );
      if (mode === "combined") {
        setQueue("all");
        setNotice(
          updated.correction
            ? "Result saved. Your manual correction still applies."
            : `Result saved. Ticket moved to ${label(queueOf(updated))}.`,
        );
      }
    } catch (e) {
      setError((e as Error).message);
      await refresh().catch(() => {});
    } finally {
      setBusy(false);
    }
  }
  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    refreshVersion.current++;
    setBusy(true);
    setError("");
    try {
      const ticket = await api<Ticket>(
        "/tickets",
        "POST",
        Object.fromEntries(form),
      );
      setTickets((current) => [ticket, ...current]);
      setQueue("all");
      setMode("combined");
      setExploring(false);
      choose(ticket);
      setNotice(
        ticket.runs[0]?.status === "failed"
          ? "Ticket saved. Automatic classification failed; you can retry below."
          : `Ticket created and classified. ${label(queueOf(ticket))}.`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function correct(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const data = Object.fromEntries(new FormData(event.currentTarget));
    refreshVersion.current++;
    setBusy(true);
    setError("");
    try {
      const updated = await api<Ticket>(
        `/tickets/${selected.id}/correction`,
        "PATCH",
        data,
      );
      setTickets((current) =>
        current.map((ticket) => (ticket.id === updated.id ? updated : ticket)),
      );
      setCorrecting(false);
      setQueue("all");
      setNotice(
        "Manual correction saved. The original model result is preserved.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function reset() {
    refreshVersion.current++;
    setBusy(true);
    setError("");
    try {
      const next = await api<Ticket[]>("/reset", "POST", {});
      setTickets(next);
      setSelectedId(next[0]?.id ?? null);
      setQueue("all");
      setMode("combined");
      setCompose(false);
      setCorrecting(false);
      setResetting(false);
      setNotice("Demo reset to four unclassified sample tickets.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const route = selected ? effective(selected) : null;
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Jev Support Desk home">
          <span className="brand-mark">
            <Layers3 size={21} />
          </span>
          <span>
            Support Desk <span className="brand-by">with Jev</span>
          </span>
        </a>
        <span className="environment">
          <span className="status-dot" />
          Local demo
        </span>
        <button
          className="quiet reset-trigger"
          disabled={busy}
          onClick={() => setResetting(!resetting)}
        >
          <RotateCcw size={15} />
          Reset demo
        </button>
      </header>
      {resetting && (
        <div className="reset-banner">
          <p>
            Delete this demo’s tickets and results, and restore the four
            samples?
          </p>
          <button disabled={busy} onClick={reset}>
            Reset tickets
          </button>
          <button className="quiet" onClick={() => setResetting(false)}>
            Cancel
          </button>
        </div>
      )}
      <main className="workspace">
        <aside className="sidebar">
          <div className="workspace-name">
            <span className="workspace-avatar">S</span>
            <div>
              <strong>Support workspace</strong>
              <span>Jev playground</span>
            </div>
          </div>
          <button
            className="new-ticket"
            disabled={busy || loading}
            onClick={() => {
              setCompose(true);
              setError("");
              setNotice("");
            }}
          >
            <Plus size={17} />
            New ticket
          </button>
          <nav aria-label="Ticket queues">
            <h2>Inbox</h2>
            {["all", "unclassified", "needs_review"].map((item) => (
              <button
                key={item}
                className={`nav-item ${queue === item ? "selected" : ""}`}
                aria-current={queue === item ? "page" : undefined}
                disabled={busy}
                onClick={() => filter(item)}
              >
                <Inbox size={16} />
                <span>{label(item)}</span>
                <span className="count">
                  {
                    tickets.filter(
                      (ticket) => item === "all" || queueOf(ticket) === item,
                    ).length
                  }
                </span>
              </button>
            ))}
            <h2>Teams</h2>
            {["billing", "technical", "account", "other"].map((item) => (
              <button
                key={item}
                className={`nav-item ${queue === item ? "selected" : ""}`}
                disabled={busy}
                onClick={() => filter(item)}
              >
                <span className={`team-dot ${item}`} />
                <span>{label(item)}</span>
                <span className="count">
                  {tickets.filter((ticket) => queueOf(ticket) === item).length}
                </span>
              </button>
            ))}
          </nav>
          <div className="sidebar-note">
            <ShieldCheck size={19} />
            <p>
              Decisions you can inspect.
              <br />
              Routing you control.
            </p>
            <span>Synthetic tickets. Real Jev requests.</span>
          </div>
        </aside>
        <section className="desk">
          <div className="desk-heading">
            <div>
              <h1>Your support inbox</h1>
              <p>Turn a customer message into a decision.</p>
            </div>
            <span className="model-name">{config?.model ?? "Jev"}</span>
          </div>
          <div className="mode-toolbar">
            <span>New tickets are classified automatically</span>
            <button
              className="quiet"
              disabled={busy}
              aria-pressed={exploring}
              onClick={() => {
                setExploring(!exploring);
                setMode("combined");
              }}
            >
              {exploring ? "Back to inbox" : "Explore question types"}
            </button>
          </div>
          {exploring && (
            <div className="mode-toolbar">
              <span id="mode-label">Demo mode</span>
              <div
                className="mode-switch"
                role="group"
                aria-labelledby="mode-label"
              >
                {MODES.map((item) => (
                  <button
                    key={item}
                    disabled={busy}
                    aria-pressed={mode === item}
                    className={mode === item ? "active" : ""}
                    onClick={() => {
                      setMode(item);
                      setError("");
                      setNotice("");
                    }}
                  >
                    {item === "combined" && <Layers3 size={14} />} {label(item)}
                  </button>
                ))}
              </div>
              <span className="mode-hint">
                {mode === "combined" ? "Apply routing" : "Preview a decision"}
              </span>
            </div>
          )}
          {error && (
            <div className="message error" role="alert">
              {error}
              {!config && (
                <button className="quiet" onClick={() => void load()}>
                  Retry connection
                </button>
              )}
            </div>
          )}
          {notice && (
            <div className="message success" role="status">
              <Check size={16} />
              {notice}
            </div>
          )}
          {config && !config.configured && (
            <div className="message warning">
              Add TYPESAFE_API_KEY to the demo’s .env file and restart the
              backend to run live classifications.
            </div>
          )}
          <div className="inbox-layout">
            <section className="ticket-list" aria-label="Tickets">
              <div className="list-heading">
                <h2>{label(queue)}</h2>
                <span>{visible.length}</span>
              </div>
              {loading ? (
                <p className="list-empty">Loading your inbox…</p>
              ) : visible.length === 0 ? (
                <p className="list-empty">No tickets in this queue yet.</p>
              ) : (
                visible.map((ticket) => (
                  <button
                    disabled={busy}
                    key={ticket.id}
                    className={`ticket-row ${selectedId === ticket.id && !compose ? "current" : ""}`}
                    aria-pressed={selectedId === ticket.id && !compose}
                    onClick={() => choose(ticket)}
                  >
                    <div className="ticket-meta">
                      <span>{ticket.customer}</span>
                      <span>{ticket.preset ?? "Custom"}</span>
                    </div>
                    <h3>{ticket.subject}</h3>
                    <p>{ticket.body}</p>
                    <div className="ticket-tags">
                      <span className={`ticket-status ${queueOf(ticket)}`}>
                        {label(queueOf(ticket))}
                      </span>
                      {effective(ticket)?.priority === "urgent" && (
                        <span className="urgent-label">Urgent</span>
                      )}
                      {ticket.correction && <span>Reviewed</span>}
                    </div>
                  </button>
                ))
              )}
              <div className="preset-note">
                Select a sample to try a refund, an outage, an unclear request,
                or account access.
              </div>
            </section>
            <section className="detail" aria-label="Ticket detail">
              {compose ? (
                <form className="compose" onSubmit={create}>
                  <div className="section-heading">
                    <h2>Create a ticket</h2>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label="Cancel new ticket"
                      onClick={() => setCompose(false)}
                    >
                      <X size={19} />
                    </button>
                  </div>
                  <p>
                    Write a customer message. Jev will assign its team and
                    priority when you create it.
                  </p>
                  <label>
                    Customer name
                    <input
                      name="customer"
                      required
                      maxLength={80}
                      defaultValue="Demo customer"
                    />
                  </label>
                  <label>
                    Subject
                    <input
                      name="subject"
                      required
                      maxLength={160}
                      placeholder="What does the customer need?"
                      autoFocus
                    />
                  </label>
                  <label>
                    Message
                    <textarea
                      name="body"
                      required
                      maxLength={8000}
                      rows={7}
                      placeholder="Include how the problem affects their work."
                    />
                  </label>
                  <button className="primary" disabled={busy}>
                    {busy ? "Creating and classifying…" : "Create ticket"}
                    <ArrowRight size={16} />
                  </button>
                </form>
              ) : selected ? (
                <>
                  <div className="ticket-content">
                    <div className="detail-meta">
                      <span>
                        <Mail size={15} />
                        {selected.customer}
                      </span>
                      <span>
                        {selected.preset
                          ? `${selected.preset} sample`
                          : "Custom ticket"}
                      </span>
                    </div>
                    <h2>{selected.subject}</h2>
                    <p className="ticket-body">{selected.body}</p>
                    {route && (
                      <div className="saved-routing">
                        <span>
                          {selected.correction
                            ? "Manual decision"
                            : "Saved routing"}
                        </span>
                        <strong>
                          {label(route.team)} · {label(route.priority)}
                        </strong>
                        <button
                          className="quiet"
                          disabled={busy}
                          onClick={() => setCorrecting(!correcting)}
                        >
                          <SlidersHorizontal size={14} />
                          Correct
                        </button>
                      </div>
                    )}
                    {correcting && (
                      <form className="correction-form" onSubmit={correct}>
                        <label>
                          Team
                          <select name="team" defaultValue={route?.team}>
                            {["billing", "technical", "account", "other"].map(
                              (item) => (
                                <option key={item} value={item}>
                                  {label(item)}
                                </option>
                              ),
                            )}
                          </select>
                        </label>
                        <label>
                          Priority
                          <select
                            name="priority"
                            defaultValue={route?.priority}
                          >
                            {["standard", "urgent", "needs_review"].map(
                              (item) => (
                                <option key={item} value={item}>
                                  {label(item)}
                                </option>
                              ),
                            )}
                          </select>
                        </label>
                        <button disabled={busy}>Save correction</button>
                      </form>
                    )}
                  </div>
                  <div className="decision-panel">
                    {exploring && (
                      <>
                        <div className="decision-heading">
                          <span className="type-label">{label(mode)}</span>
                          <span>
                            {mode === "combined"
                              ? "4 questions · 1 request"
                              : "1 question · 1 request"}
                          </span>
                        </div>
                        <h3>{modeCopy[mode].title}</h3>
                        <p className="decision-description">
                          {modeCopy[mode].description}
                        </p>
                        {mode === "combined" && (
                          <div className="question-list">
                            <span>
                              <b>Choice</b> Team
                            </span>
                            <span>
                              <b>Noul</b> Refund requested
                            </span>
                            <span>
                              <b>Score</b> Impact
                            </span>
                            <span>
                              <b>Noul</b> Impact stated
                            </span>
                          </div>
                        )}
                        <details className="question-details">
                          <summary>
                            Inspect the question{mode === "combined" ? "s" : ""}
                            <ChevronDown size={14} />
                          </summary>
                          {config &&
                            Object.entries(config.modes[mode].questions).map(
                              ([key, question]) => (
                                <div key={key}>
                                  <strong>
                                    {key} · {question.type}
                                  </strong>
                                  <p>{question.instructions}</p>
                                  {question.criteria && (
                                    <ul>
                                      {Object.entries(question.criteria).map(
                                        ([name, description]) => (
                                          <li key={name}>
                                            <b>{label(name)}</b>: {description}
                                          </li>
                                        ),
                                      )}
                                    </ul>
                                  )}
                                </div>
                              ),
                            )}
                        </details>
                      </>
                    )}
                    {(exploring || !run?.result) && (
                      <div className="run-row">
                        <button
                          className="primary"
                          disabled={busy || active || !config?.configured}
                          onClick={() => void classify()}
                        >
                          {busy || active ? (
                            <LoaderCircle size={17} className="spinner" />
                          ) : (
                            <Sparkles size={17} />
                          )}{" "}
                          {busy || active
                            ? "Classifying…"
                            : exploring
                              ? "Run classification"
                              : run?.status === "failed"
                                ? "Retry classification"
                                : "Classify sample"}
                          {!busy && !active && <ArrowRight size={16} />}
                        </button>
                        <span>
                          {mode === "combined"
                            ? "Saves the routing decision"
                            : "Leaves the ticket’s queue unchanged"}
                        </span>
                      </div>
                    )}
                    <div
                      className="results"
                      aria-live="polite"
                      aria-busy={busy || active}
                    >
                      {busy || active ? (
                        <p className="result-placeholder">
                          Asking Jev. Your ticket is saved.
                        </p>
                      ) : run?.status === "failed" ? (
                        <div className="result-error">
                          <strong>Classification did not complete</strong>
                          <p>{run.error}</p>
                        </div>
                      ) : run?.result && config ? (
                        <>
                          <div className="result-heading">
                            <strong>Classified by Jev</strong>
                            <span>{run.result.elapsed_ms.toFixed(0)} ms</span>
                          </div>
                          {exploring &&
                            Object.entries(config.modes[mode].questions).map(
                              ([key, question]) => (
                                <AnswerView
                                  key={run.id + key}
                                  question={question}
                                  answer={run.result!.raw.answers[key]}
                                />
                              ),
                            )}
                          {run.result.policy && (
                            <div
                              className={`policy ${run.result.policy.review_required ? "review" : ""}`}
                            >
                              <strong>
                                {run.result.policy.review_required
                                  ? "Send to human review"
                                  : `Route to ${label(run.result.policy.team)}`}
                              </strong>
                              <p>
                                {label(run.result.policy.priority)} priority ·
                                Refund{" "}
                                {run.result.policy.refund?.replaceAll("_", " ")}
                              </p>
                              {run.result.policy.reasons?.map((reason) => (
                                <p key={reason}>{reason}</p>
                              ))}
                              <span>
                                Python applies these rules. A refund flag never
                                approves a payment.
                              </span>
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="result-placeholder">
                          <span className="empty-result-icon">
                            <Layers3 size={22} />
                          </span>
                          <strong>Your decision will appear here</strong>
                          <p>
                            {exploring
                              ? `Run ${label(mode)} to see the actual model response.`
                              : "This sample is ready to classify. New tickets are classified automatically."}
                          </p>
                        </div>
                      )}
                    </div>
                    {exploring && (
                      <div className="developer-details">
                        <details>
                          <summary>
                            <Code2 size={16} />
                            Python code
                            <ChevronDown size={14} />
                          </summary>
                          <p>
                            This runnable example uses the same question
                            definitions as the app. Replace its sample ticket to
                            try your own.
                          </p>
                          <pre>
                            <code>{config?.modes[mode].python}</code>
                          </pre>
                        </details>
                        <details>
                          <summary>
                            <Layers3 size={16} />
                            Raw response
                            <ChevronDown size={14} />
                          </summary>
                          <pre>
                            {run?.result
                              ? JSON.stringify(run.result.raw, null, 2)
                              : "Run classification to see a response."}
                          </pre>
                        </details>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="empty-detail">
                  <Inbox size={32} />
                  <h2>
                    {loading ? "Opening the inbox" : "Nothing waiting here"}
                  </h2>
                  <p>
                    {loading
                      ? "Loading sample tickets and demo modes."
                      : "Choose another queue or create a ticket to explore Jev."}
                  </p>
                </div>
              )}
            </section>
          </div>
        </section>
      </main>
    </div>
  );
}
