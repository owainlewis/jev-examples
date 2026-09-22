import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDownLeft,
  ArrowUpRight,
  Pause,
  Play,
  RotateCcw,
  ExternalLink,
} from "lucide-react";
import { Button } from "./components/ui/button";

type Point = { time: number; price: number };
type Event = {
  time: number;
  action: string;
  probability: number;
  latency: number;
  status: string;
  fill: number | null;
  quantity?: number;
  filled_at?: number;
};
type State = {
  mode: string;
  feed_status: string;
  error: string | null;
  thinking: boolean;
  has_key: boolean;
  running: boolean;
  points: Point[];
  events: Event[];
  last: { bid: number; ask: number } | null;
  quote_age: number | null;
  cash: number;
  quantity: number;
  equity: number;
  net_profit: number;
  realized: number;
  unrealized: number;
  fees: number;
  drawdown_pct: number;
  benchmark_profit: number;
  calls: number;
  latency: number | null;
  probabilities: Record<string, number> | null;
  choice: string | null;
  model: string;
  trade_count: number;
};
const usd = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(n);
const clock = (t: number) =>
  new Date(t * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
function Chart({ points, events }: { points: Point[]; events: Event[] }) {
  if (points.length < 2)
    return (
      <div className="chart-empty">
        <Activity size={28} />
        <p>Waiting for market prices</p>
        <span>The chart will appear as quotes arrive.</span>
      </div>
    );
  const values = points.map((p) => p.price);
  const low = Math.min(...values),
    high = Math.max(...values);
  const pad = Math.max((high - low) * 0.15, 5);
  const min = low - pad,
    max = high + pad;
  const x = (i: number) => 24 + (i / (points.length - 1)) * 790;
  const y = (v: number) => 280 - ((v - min) / (max - min)) * 230;
  const line = points.map((p, i) => `${x(i)},${y(p.price)}`).join(" ");
  return (
    <svg
      viewBox="0 0 910 330"
      role="img"
      aria-label="BTC price chart with simulated trade markers"
    >
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}>
          <line
            x1="24"
            x2="815"
            y1={50 + t * 230}
            y2={50 + t * 230}
            stroke="var(--line)"
            strokeDasharray="3 6"
          />
          <text x="830" y={54 + t * 230}>
            {usd(max - t * (max - min))}
          </text>
        </g>
      ))}
      <polygon points={`24,280 ${line} 814,280`} fill="var(--chart-fill)" />
      <polyline
        points={line}
        fill="none"
        stroke="var(--ink)"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {events
        .filter((e) => e.fill && e.filled_at && e.filled_at >= points[0].time)
        .map((e) => {
          let i = points.findIndex((p) => p.time >= (e.filled_at ?? e.time));
          if (i < 0) return null;
          return (
            <circle
              key={e.time}
              cx={x(i)}
              cy={y(points[i].price)}
              r="4"
              fill={e.action === "buy" ? "var(--green)" : "var(--red)"}
              stroke="white"
              strokeWidth="1.5"
            >
              <title>
                {e.action} at {usd(e.fill!)}
              </title>
            </circle>
          );
        })}
      <circle
        cx={x(points.length - 1)}
        cy={y(values.at(-1)!)}
        r="4"
        fill="var(--green)"
      />
      <text x="24" y="318">
        {clock(points[0].time)}
      </text>
      <text x="745" y="318">
        {clock(points.at(-1)!.time)}
      </text>
    </svg>
  );
}
export default function App() {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    async function poll() {
      try {
        const r = await fetch("/api/state", { signal: controller.signal });
        if (!r.ok) throw Error("Unable to load simulator");
        const s = await r.json();
        if (active) {
          setState(s);
          setConnectionError("");
        }
      } catch (e) {
        if (active)
          setConnectionError("Connection lost. The server may be stopped.");
      }
    }
    poll();
    const id = setInterval(poll, 1000);
    return () => {
      active = false;
      controller.abort();
      clearInterval(id);
    };
  }, []);
  async function control(action: string, mode?: string) {
    setBusy(true);
    try {
      const r = await fetch("/api/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, mode }),
      });
      const s = await r.json();
      if (!r.ok) throw Error(s.detail);
      setState(s);
      setError("");
      setConfirm(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  if (!state)
    return (
      <main className="loading">
        <Activity />
        <h1>Jev trading simulator</h1>
        <p>{connectionError || "Connecting to the local server…"}</p>
      </main>
    );
  const price = state.last ? (state.last.ask + state.last.bid) / 2 : null;
  const fresh = state.quote_age !== null && state.quote_age <= 10;
  return (
    <main className="shell">
      <header>
        <div className="identity">
          <span className="brand-mark">
            <Activity size={20} />
          </span>
          <h1>Jev trader</h1>
          <span className="badge">Simulation only</span>
        </div>
        <a
          href="https://docs.typesafe.ai/introduction"
          target="_blank"
          rel="noreferrer"
        >
          Built with Jev <ExternalLink size={13} />
        </a>
      </header>
      <section className="toolbar">
        <div className="feed">
          <span className={`dot ${fresh ? "connected" : ""}`} />
          {fresh ? state.feed_status : "Waiting for fresh data"}
          <span className="divider">/</span>
          <span>BTC–USD</span>
        </div>
        <div className="controls">
          <label className="sr-only" htmlFor="mode">
            Price source
          </label>
          <select
            id="mode"
            value={state.mode}
            disabled={busy}
            onChange={(e) => setConfirm(e.target.value)}
          >
            <option value="live">Live market</option>
            <option value="replay">Synthetic replay</option>
          </select>
          <Button
            variant="outline"
            size="icon"
            aria-label="Reset portfolio"
            onClick={() => setConfirm(state.mode)}
            disabled={busy}
          >
            <RotateCcw size={15} />
          </Button>
          <Button
            className="run"
            disabled={busy || (!state.running && (!fresh || !state.has_key))}
            onClick={() => control(state.running ? "pause" : "start")}
          >
            {state.running ? <Pause size={14} /> : <Play size={14} />}{" "}
            {state.running ? "Pause" : "Start simulation"}
          </Button>
        </div>
      </section>
      {confirm && (
        <div className="notice" role="alert">
          <span>
            Reset the portfolio to $10,000 and{" "}
            {confirm === "replay" ? "use synthetic prices" : "use live prices"}?
            Current results remain in the local snapshot history.
          </span>
          <Button
            size="sm"
            onClick={() => control("reset", confirm)}
            disabled={busy}
          >
            Reset and switch
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setConfirm(null)}>
            Cancel
          </Button>
        </div>
      )}
      {(connectionError || error || state.error || !state.has_key) && (
        <div className="notice warning" role="alert">
          {connectionError ||
            error ||
            state.error ||
            "Add TYPESAFE_API_KEY to this demo’s .env file and restart the server to enable Jev decisions."}
        </div>
      )}
      {state.mode === "replay" && (
        <div className="replay-note">
          Synthetic replay · generated prices, real Jev calls. These are not
          historical market results.
        </div>
      )}
      <div className="workspace">
        <section className="market">
          <div className="market-head">
            <div>
              <p className="label">
                Bitcoin <span>BTC / USD</span>
              </p>
              <div className="price">{price ? usd(price) : "—"}</div>
              <p className="muted">
                {state.quantity > 0
                  ? `Long ${state.quantity.toFixed(6)} BTC`
                  : "No open position"}
                <span className="middle-dot">·</span>
                <span
                  className={state.net_profit >= 0 ? "positive" : "negative"}
                >
                  {usd(state.net_profit)} net
                </span>
              </p>
            </div>
            <div className="decision-status">
              <span className={state.running ? "positive" : ""}>
                {state.thinking
                  ? "Evaluating…"
                  : state.running
                    ? "Running"
                    : "Paused"}
              </span>
              <small>
                {state.latency !== null
                  ? `${state.latency.toLocaleString()} ms last call`
                  : "Ready when you are"}
              </small>
            </div>
          </div>
          <Chart points={state.points} events={state.events} />
          <div className="chart-legend">
            <span>
              <i className="buy" />
              Buy
            </span>
            <span>
              <i className="sell" />
              Sell
            </span>
            <span className="muted">
              {state.points.length} quotes ·{" "}
              {state.quote_age !== null
                ? `${state.quote_age}s since last quote`
                : "Connecting"}
            </span>
          </div>
          <div className="portfolio">
            <div>
              <p className="label">Portfolio value</p>
              <strong>{usd(state.equity)}</strong>
            </div>
            <div>
              <p className="label">Simulated net profit</p>
              <strong
                className={state.net_profit >= 0 ? "positive" : "negative"}
              >
                {usd(state.net_profit)}
              </strong>
            </div>
            <div>
              <p className="label">Available cash</p>
              <strong>{usd(state.cash)}</strong>
            </div>
          </div>
          <dl className="details">
            <div>
              <dt>Realized</dt>
              <dd>{usd(state.realized)}</dd>
            </div>
            <div>
              <dt>Unrealized, after exit costs</dt>
              <dd>{usd(state.unrealized)}</dd>
            </div>
            <div>
              <dt>Fees paid</dt>
              <dd>{usd(state.fees)}</dd>
            </div>
            <div>
              <dt>Maximum drawdown</dt>
              <dd>{state.drawdown_pct.toFixed(2)}%</dd>
            </div>
            <div>
              <dt>Buy-and-hold net profit</dt>
              <dd>{usd(state.benchmark_profit)}</dd>
            </div>
          </dl>
        </section>
        <aside>
          <section className="strategy">
            <h2>Trading policy</h2>
            <p>
              Follow short-term momentum. Buy when the trend strengthens. Sell
              when it weakens. Hold when the evidence is mixed.
            </p>
            <div className="policy-tags">
              <span>$1,000 per position</span>
              <span>No leverage</span>
            </div>
          </section>
          <section className="probabilities">
            <div className="section-title">
              <h2>Jev decision</h2>
              <span>{state.calls} calls</span>
            </div>
            <div
              className={`action ${state.choice === "buy" ? "positive" : state.choice === "sell" ? "negative" : ""}`}
            >
              {state.choice ? state.choice.toUpperCase() : "WAITING"}
              <small>
                {state.probabilities && state.choice
                  ? `${Math.round(state.probabilities[state.choice] * 100)}%`
                  : ""}
              </small>
            </div>
            {["buy", "hold", "sell"].map((action) => (
              <div className="prob-row" key={action}>
                <span>{action}</span>
                <div className="track">
                  <div
                    className={action}
                    style={{
                      width: `${(state.probabilities?.[action] || 0) * 100}%`,
                    }}
                  />
                </div>
                <b>
                  {state.probabilities
                    ? `${Math.round(state.probabilities[action] * 100)}%`
                    : "—"}
                </b>
              </div>
            ))}
            <p className="fine">
              Action probabilities, not the chance of profit. Below 75%: no
              trade.
            </p>
          </section>
          <section className="execution">
            <h2>Execution assumptions</h2>
            <dl>
              <div>
                <dt>Trading fee</dt>
                <dd>0.10% per side</dd>
              </div>
              <div>
                <dt>Slippage</dt>
                <dd>0.05% per side</dd>
              </div>
              <div>
                <dt>Fill price</dt>
                <dd>Next bid / ask</dd>
              </div>
              <div>
                <dt>Decision interval</dt>
                <dd>15s after each call</dd>
              </div>
            </dl>
            <p className="fine">
              Real Jev calls. Virtual orders only. No exchange account is
              connected.
            </p>
          </section>
        </aside>
      </div>
      <section className="journal">
        <div className="section-title">
          <h2>Decision feed</h2>
          <span>{state.model}</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>Probability</th>
                <th>Latency</th>
                <th>Fill price</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {state.events.length ? (
                state.events.map((e) => (
                  <tr key={e.time}>
                    <td>{clock(e.time)}</td>
                    <td
                      className={
                        e.action === "buy"
                          ? "positive"
                          : e.action === "sell"
                            ? "negative"
                            : ""
                      }
                    >
                      <span className="action-cell">
                        {e.action === "buy" ? (
                          <ArrowUpRight size={14} />
                        ) : e.action === "sell" ? (
                          <ArrowDownLeft size={14} />
                        ) : null}
                        {e.action.toUpperCase()}
                      </span>
                    </td>
                    <td>{Math.round(e.probability * 100)}%</td>
                    <td>{e.latency} ms</td>
                    <td>{e.fill ? usd(e.fill) : "—"}</td>
                    <td>{e.status}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="empty">
                    {state.running
                      ? state.points.length < 30
                        ? "Collecting 30 quotes before the first Jev decision…"
                        : "Waiting for the first Jev decision…"
                      : "Start the simulation to see Jev decisions and simulated trades."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <footer>
        <span>Starting balance $10,000 · BTC-USD only</span>
        <span>
          Simulated results include spread, fees, and assumed slippage.
        </span>
      </footer>
    </main>
  );
}
