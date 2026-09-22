// @vitest-environment jsdom
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";

const ticket = {
  id: "ticket-1",
  subject: "A refund",
  body: "Refund the duplicate payment, please.",
  customer: "Sam",
  preset: "Refund",
  routing: { team: "billing", priority: "standard" },
  correction: null,
  runs: [
    {
      id: "run-1",
      mode: "choice",
      status: "running",
      result: null,
      error: null,
    },
  ],
};
const config = {
  configured: true,
  model: "test-model",
  modes: Object.fromEntries(
    ["choice", "noul", "score", "combined"].map((mode) => [
      mode,
      { questions: {}, python: "# Example" },
    ]),
  ),
};
const response = (data: unknown) =>
  new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
let resolvePoll: (value: Response) => void;
let reads: number;

beforeEach(() => {
  vi.useFakeTimers();
  reads = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, options: RequestInit) => {
      if (url === "/api/config") return Promise.resolve(response(config));
      if (url === "/api/tickets") {
        reads++;
        if (reads === 1) return Promise.resolve(response([ticket]));
        return new Promise<Response>((resolve) => {
          resolvePoll = resolve;
        });
      }
      if (url.endsWith("/correction"))
        return Promise.resolve(
          response({
            ...ticket,
            correction: JSON.parse(options.body as string),
          }),
        );
      if (url === "/api/reset")
        return Promise.resolve(
          response([
            {
              ...ticket,
              id: "new-ticket",
              subject: "Fresh sample",
              routing: null,
              runs: [],
            },
          ]),
        );
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

async function openWithPendingPoll() {
  await act(async () => {
    render(<App />);
  });
  await act(async () => {
    vi.advanceTimersByTime(2000);
  });
  expect(reads).toBe(2);
}

test("switching modes keeps the ticket and makes no mutation request", async () => {
  await act(async () => {
    render(<App />);
  });
  for (const mode of ["Noul", "Score", "Combined", "Choice"]) {
    fireEvent.click(screen.getByRole("button", { name: mode }));
    expect(
      screen.getByRole("heading", { name: "A refund", level: 2 }),
    ).toBeTruthy();
  }
  expect(
    vi
      .mocked(fetch)
      .mock.calls.every(([, options]) => options?.method === "GET"),
  ).toBe(true);
});

test("a late poll cannot remove a saved human correction", async () => {
  await openWithPendingPoll();
  fireEvent.click(screen.getByRole("button", { name: "Correct" }));
  fireEvent.change(screen.getByLabelText("Team", { exact: true }), {
    target: { value: "account" },
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  });
  expect(screen.getByText("Manual decision")).toBeTruthy();
  await act(async () => {
    resolvePoll(response([{ ...ticket, runs: [] }]));
  });
  expect(screen.getByText("Manual decision")).toBeTruthy();
  expect(screen.getByText("Account · Standard")).toBeTruthy();
});

test("a late poll cannot restore tickets removed by reset", async () => {
  await openWithPendingPoll();
  fireEvent.click(screen.getByRole("button", { name: "Reset demo" }));
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Reset tickets" }));
  });
  expect(
    screen.getByRole("heading", { name: "Fresh sample", level: 2 }),
  ).toBeTruthy();
  await act(async () => {
    resolvePoll(response([{ ...ticket, runs: [] }]));
  });
  expect(
    screen.getByRole("heading", { name: "Fresh sample", level: 2 }),
  ).toBeTruthy();
  expect(
    screen.queryByRole("heading", { name: "A refund", level: 2 }),
  ).toBeNull();
});
