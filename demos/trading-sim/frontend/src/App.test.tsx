// @vitest-environment jsdom
import {
  cleanup,
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App";
const state = {
  mode: "live",
  feed_status: "Connected",
  error: null,
  thinking: false,
  has_key: true,
  running: false,
  points: [],
  events: [],
  last: null,
  quote_age: null,
  cash: 10000,
  quantity: 0,
  equity: 10000,
  net_profit: 0,
  realized: 0,
  unrealized: 0,
  fees: 0,
  drawdown_pct: 0,
  benchmark_profit: 0,
  calls: 0,
  latency: null,
  probabilities: null,
  choice: null,
  model: "jev-1.13.0",
  trade_count: 0,
};
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
it("clears the connection error when polling recovers", async () => {
  let succeed = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      if (!succeed) throw Error("offline");
      return { ok: true, json: async () => state };
    }),
  );
  render(<App />);
  await screen.findByText("Connection lost. The server may be stopped.");
  succeed = true;
  await screen.findByRole("heading", { name: "Jev trader" }, { timeout: 2500 });
  expect(
    screen.queryByText("Connection lost. The server may be stopped."),
  ).toBeNull();
});
it("requires confirmation before resetting a portfolio", async () => {
  const fetcher = vi.fn(async () => ({ ok: true, json: async () => state }));
  vi.stubGlobal("fetch", fetcher);
  render(<App />);
  await screen.findByRole("heading", { name: "Jev trader" });
  fireEvent.click(screen.getByRole("button", { name: "Reset portfolio" }));
  expect(fetcher.mock.calls.length).toBe(1);
  fireEvent.click(screen.getByRole("button", { name: "Reset and switch" }));
  await waitFor(() => expect(fetcher.mock.calls.length).toBe(2));
});
