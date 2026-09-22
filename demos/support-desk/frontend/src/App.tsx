import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  Inbox,
  LoaderCircle,
  Plus,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import "./style.css";

type Decision = {
  choice: string;
  probability: number;
  probabilities: Record<string, number>;
  needs_review: boolean;
};
type Classification = {
  department: Decision;
  priority: Decision;
  review_required: boolean;
};
type Ticket = {
  id: string;
  subject: string;
  body: string;
  created_at: number;
  classification: Classification | null;
  status: string;
  error: string | null;
  elapsed_ms: number | null;
};
type Config = { configured: boolean; model: string; review_threshold: number };
const names: Record<string, string> = {
  hr: "HR",
  finance: "Finance",
  engineering: "Engineering",
  it_support: "IT Support",
  other: "Other",
  low: "Low",
  normal: "Normal",
  high: "High",
  critical: "Critical",
};
const label = (value: string) => names[value] ?? value;
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
const examples = [
  {
    name: "HR · routine request",
    subject: "Where can I find our parental leave policy?",
    body: "I would like to read the company's parental leave policy. This is a routine question with no deadline and no impact on my work.",
  },
  {
    name: "Finance · invoice issue",
    subject: "Incorrect supplier invoice total",
    body: "A supplier invoice shows the wrong total. Could Finance check the calculation? Work can continue and there is no payment deadline at risk.",
  },
  {
    name: "IT Support · blocked employee",
    subject: "I cannot sign in to GitHub",
    body: "My company GitHub account is locked. I cannot access any repositories and cannot do my work. Only my account is affected. Please restore my access.",
  },
  {
    name: "Engineering · production outage",
    subject: "Our product is down for every customer",
    body: "Our production API is returning 500 errors for all customers. Every customer is unable to use the product, and we are losing transactions right now. Please restore production service.",
  },
  {
    name: "Unclear request",
    subject: "I need help with a request",
    body: "I am not sure who owns this. There is a problem with a request and somebody needs to look at it.",
  },
];
async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Demo-Request": "support-desk",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : "The request failed. Check your input and try again.",
    );
  }
  return response.json();
}
function Field({
  value,
  priority = false,
}: {
  value?: Decision;
  priority?: boolean;
}) {
  if (!value) return <span className="muted">Not classified</span>;
  return (
    <div className="field">
      {priority ? (
        <Badge variant="secondary" className={`priority ${value.choice}`}>
          {label(value.choice)}
        </Badge>
      ) : (
        <span className="department">{label(value.choice)}</span>
      )}
      <span className="probability">{percent(value.probability)}</span>
      {value.needs_review && <span className="field-review">Needs review</span>}
    </div>
  );
}
function Distribution({
  title,
  decision,
}: {
  title: string;
  decision: Decision;
}) {
  return (
    <section className="distribution">
      <h3>{title}</h3>
      {Object.entries(decision.probabilities)
        .sort((a, b) => b[1] - a[1])
        .map(([name, probability]) => (
          <div className="distribution-row" key={name}>
            <div>
              <span>{label(name)}</span>
              <span>{percent(probability)}</span>
            </div>
            <div className="bar">
              <span style={{ width: `${probability * 100}%` }} />
            </div>
          </div>
        ))}
    </section>
  );
}
export function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [compose, setCompose] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const version = useRef(0);
  async function load() {
    setLoading(true);
    setError("");
    try {
      const [settings, queue] = await Promise.all([
        api<Config>("/config"),
        api<Ticket[]>("/tickets"),
      ]);
      setConfig(settings);
      setTickets(queue);
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
    if (busy || !tickets.some((ticket) => ticket.status === "running")) return;
    const generation = ++version.current;
    const timer = window.setInterval(() => {
      void api<Ticket[]>("/tickets")
        .then((next) => {
          if (generation === version.current) setTickets(next);
        })
        .catch((e) => {
          if (generation === version.current) setError(e.message);
        });
    }, 2000);
    return () => {
      window.clearInterval(timer);
      version.current++;
    };
  }, [tickets, busy]);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    version.current++;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const ticket = await api<Ticket>("/tickets", "POST", { subject, body });
      setTickets((current) => [ticket, ...current]);
      setCompose(false);
      setSubject("");
      setBody("");
      setSelected(ticket.id);
      setFilter("all");
      setNotice(
        ticket.status === "failed"
          ? "Ticket saved. Classification failed; retry below."
          : "Ticket created and classified.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function retry(ticket: Ticket) {
    version.current++;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await api<Ticket>(
        `/tickets/${ticket.id}/runs`,
        "POST",
        {},
      );
      setTickets((current) =>
        current.map((item) => (item.id === ticket.id ? updated : item)),
      );
      setNotice("Classification updated.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const reviewCount = tickets.filter(
    (ticket) => ticket.classification?.review_required,
  ).length;
  const visible = tickets.filter(
    (ticket) => filter === "all" || ticket.classification?.review_required,
  );
  return (
    <div className="app">
      <header>
        <a href="/" className="brand">
          <span className="brand-icon">
            <Inbox size={20} />
          </span>
          Support Desk
        </a>
        <span className="powered">Powered by Jev</span>
      </header>
      <main>
        <div className="page-heading">
          <div>
            <h1>Ticket queue</h1>
            <p>Every request finds the right department.</p>
          </div>
          <Button
            className="primary"
            disabled={busy || loading}
            onClick={() => {
              setCompose(true);
              setError("");
              setNotice("");
            }}
          >
            <Plus size={17} />
            New ticket
          </Button>
        </div>
        {error && (
          <div className="alert error" role="alert">
            {error}
            {!config && (
              <Button onClick={() => void load()}>Retry connection</Button>
            )}
          </div>
        )}
        {notice && (
          <div className="alert success" role="status">
            <Check size={16} />
            {notice}
          </div>
        )}
        {config && !config.configured && (
          <div className="alert warning">
            Add TYPESAFE_API_KEY to the demo’s .env file and restart the
            backend. Tickets will still be saved if classification fails.
          </div>
        )}
        {compose && (
          <form className="composer" onSubmit={create}>
            <div className="composer-heading">
              <h2>New ticket</h2>
              <Button
                variant="ghost"
                size="icon"
                type="button"
                className="icon-button"
                aria-label="Cancel new ticket"
                disabled={busy}
                onClick={() => setCompose(false)}
              >
                <X size={19} />
              </Button>
            </div>
            <p>
              Jev will classify the department and priority when you create it.
            </p>
            <label className="example-label">
              Try an example
              <NativeSelect
                defaultValue=""
                disabled={busy}
                onChange={(event) => {
                  const example = examples[Number(event.target.value)];
                  if (example) {
                    setSubject(example.subject);
                    setBody(example.body);
                  }
                }}
              >
                <NativeSelectOption value="" disabled>
                  Choose a sample request
                </NativeSelectOption>
                {examples.map((example, index) => (
                  <NativeSelectOption value={index} key={example.name}>
                    {example.name}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </label>
            <label>
              Subject
              <Input
                autoFocus
                required
                maxLength={160}
                value={subject}
                disabled={busy}
                onChange={(event) => setSubject(event.target.value)}
                placeholder="What do you need help with?"
              />
            </label>
            <label>
              Message
              <Textarea
                required
                maxLength={8000}
                rows={4}
                disabled={busy}
                value={body}
                onChange={(event) => setBody(event.target.value)}
                placeholder="Describe the issue, its impact, and any deadline."
              />
            </label>
            <div className="form-footer">
              <span>Two classifications. One Jev request.</span>
              <Button className="primary" disabled={busy}>
                {busy ? (
                  <LoaderCircle size={16} className="spinner" />
                ) : (
                  <ArrowRight size={16} />
                )}{" "}
                {busy ? "Creating and classifying…" : "Create ticket"}
              </Button>
            </div>
          </form>
        )}
        <div className="queue-toolbar">
          <div className="filters" role="group" aria-label="Ticket filter">
            <Button
              variant="ghost"
              aria-pressed={filter === "all"}
              onClick={() => setFilter("all")}
            >
              All tickets <span>{tickets.length}</span>
            </Button>
            <Button
              variant="ghost"
              aria-pressed={filter === "review"}
              onClick={() => setFilter("review")}
            >
              Needs review <span>{reviewCount}</span>
            </Button>
          </div>
          <span className="threshold">
            Below {percent(config?.review_threshold ?? 0.8)} goes to review
          </span>
        </div>
        <section className="queue" aria-label="Ticket queue">
          {loading ? (
            <div className="empty">Loading tickets…</div>
          ) : visible.length === 0 ? (
            <div className="empty">
              <Inbox size={28} />
              <h2>
                {filter === "review"
                  ? "Nothing needs review"
                  : "Your queue is ready"}
              </h2>
              <p>
                {filter === "review"
                  ? "Tickets with an uncertain department or priority will appear here."
                  : "Create a ticket to see its department, priority, and probabilities."}
              </p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th scope="col">Request</th>
                  <th scope="col">Department</th>
                  <th scope="col">Priority</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((ticket) => (
                  <TicketRows
                    key={ticket.id}
                    ticket={ticket}
                    expanded={selected === ticket.id}
                    busy={busy}
                    onSelect={() =>
                      setSelected(selected === ticket.id ? null : ticket.id)
                    }
                    onRetry={() => void retry(ticket)}
                  />
                ))}
              </tbody>
            </table>
          )}
        </section>
        <p className="footnote">
          Probabilities are the model’s estimates, not measured accuracy. The
          80% review threshold is a demo starting point.
        </p>
      </main>
    </div>
  );
}
function TicketRows({
  ticket,
  expanded,
  busy,
  onSelect,
  onRetry,
}: {
  ticket: Ticket;
  expanded: boolean;
  busy: boolean;
  onSelect: () => void;
  onRetry: () => void;
}) {
  const result = ticket.classification;
  const state =
    ticket.status === "running"
      ? "Classifying"
      : ticket.status === "failed"
        ? "Failed"
        : !result
          ? "Not classified"
          : result.review_required
            ? "Needs review"
            : "Classified";
  return (
    <>
      <tr className={expanded ? "selected" : ""}>
        <td data-label="Request">
          <Button
            variant="ghost"
            className="ticket-title"
            aria-expanded={expanded}
            onClick={onSelect}
          >
            {ticket.subject}
            <ChevronDown size={16} />
          </Button>
        </td>
        <td data-label="Department">
          <Field value={result?.department} />
        </td>
        <td data-label="Priority">
          <Field value={result?.priority} priority />
        </td>
        <td data-label="Status">
          <Badge
            variant="secondary"
            className={`status ${state === "Needs review" ? "review" : ticket.status}`}
          >
            {state}
          </Badge>
        </td>
      </tr>
      {expanded && (
        <tr className="detail-row">
          <td colSpan={4}>
            <div className="ticket-detail">
              <div className="message-copy">
                <h2>{ticket.subject}</h2>
                <p>{ticket.body}</p>
                {ticket.error && (
                  <div className="alert error" role="alert">
                    {ticket.error}
                  </div>
                )}
                {!result && ticket.status !== "running" && (
                  <Button disabled={busy} onClick={onRetry}>
                    {busy
                      ? "Classifying…"
                      : ticket.status === "failed"
                        ? "Retry classification"
                        : "Classify ticket"}
                  </Button>
                )}
                {ticket.status === "running" && (
                  <p className="muted">Classification is in progress.</p>
                )}
                {ticket.elapsed_ms !== null && (
                  <span className="timing">
                    Classified by Jev · {ticket.elapsed_ms.toFixed(0)} ms
                  </span>
                )}
              </div>
              {result && (
                <div className="probabilities">
                  <Distribution
                    title="Department probabilities"
                    decision={result.department}
                  />
                  <Distribution
                    title="Priority probabilities"
                    decision={result.priority}
                  />
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
