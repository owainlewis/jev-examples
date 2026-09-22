// @vitest-environment jsdom
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "./App";

const classification = {
  department: {
    choice: "it_support",
    probability: 0.94,
    probabilities: {
      it_support: 0.94,
      engineering: 0.03,
      hr: 0.01,
      finance: 0.01,
      other: 0.01,
    },
    needs_review: false,
  },
  priority: {
    choice: "high",
    probability: 0.78,
    probabilities: { high: 0.78, normal: 0.2, low: 0.01, critical: 0.01 },
    needs_review: true,
  },
  review_required: true,
};
const ticket = {
  id: "one",
  subject: "GitHub is locked",
  body: "My work account is locked.",
  created_at: 0,
  status: "succeeded",
  classification,
  error: null,
  elapsed_ms: 180,
};
const response = (value: unknown) =>
  new Response(JSON.stringify(value), { status: 200 });
function mockQueue(queue: unknown[] = [ticket]) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, options: RequestInit) => {
      if (url === "/api/config")
        return Promise.resolve(
          response({
            configured: true,
            model: "test-model",
            review_threshold: 0.8,
          }),
        );
      if (url === "/api/tickets" && options.method === "GET")
        return Promise.resolve(response(queue));
      if (url === "/api/tickets" && options.method === "POST")
        return Promise.resolve(
          response({
            ...ticket,
            id: "created",
            ...JSON.parse(options.body as string),
          }),
        );
      if (url.endsWith("/runs")) return Promise.resolve(response(ticket));
      throw new Error(url);
    }),
  );
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

test("queue shows both category probabilities and flags only uncertain field", async () => {
  mockQueue();
  await act(async () => {
    render(<App />);
  });
  const row = screen.getByRole("row", { name: /GitHub is locked/ });
  expect(within(row).getByText("IT Support")).toBeTruthy();
  expect(within(row).getByText("94.0%")).toBeTruthy();
  expect(within(row).getByText("High")).toBeTruthy();
  expect(within(row).getByText("78.0%")).toBeTruthy();
  expect(within(row).getAllByText("Needs review").length).toBe(2);
  fireEvent.click(screen.getByRole("button", { name: "GitHub is locked" }));
  expect(screen.getByText("Department probabilities")).toBeTruthy();
  expect(screen.getByText("Priority probabilities")).toBeTruthy();
  expect(screen.getByText("My work account is locked.")).toBeTruthy();
});

test("create needs only subject and message and makes one request", async () => {
  mockQueue([]);
  await act(async () => {
    render(<App />);
  });
  expect(screen.getByText("Your queue is ready")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "New ticket" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Subject" }), {
    target: { value: "New request" },
  });
  fireEvent.change(screen.getByRole("textbox", { name: "Message" }), {
    target: { value: "Need access" },
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Create ticket" }));
  });
  expect(screen.getByRole("button", { name: "New request" })).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: "Explore question types" }),
  ).toBeNull();
  expect(
    vi
      .mocked(fetch)
      .mock.calls.filter(([, options]) => options?.method === "POST").length,
  ).toBe(1);
});

test("failed ticket retains message and offers retry", async () => {
  mockQueue([
    {
      ...ticket,
      classification: null,
      status: "failed",
      error: "Jev could not complete the request.",
    },
  ]);
  await act(async () => {
    render(<App />);
  });
  fireEvent.click(screen.getByRole("button", { name: "GitHub is locked" }));
  expect(screen.getByText("My work account is locked.")).toBeTruthy();
  await act(async () => {
    fireEvent.click(
      screen.getByRole("button", { name: "Retry classification" }),
    );
  });
  expect(screen.getByText("Classification updated.")).toBeTruthy();
});

test("needs review filter excludes accepted tickets", async () => {
  mockQueue([
    {
      ...ticket,
      classification: {
        ...classification,
        review_required: false,
        priority: {
          ...classification.priority,
          needs_review: false,
          probability: 0.9,
        },
      },
    },
  ]);
  await act(async () => {
    render(<App />);
  });
  fireEvent.click(screen.getByRole("button", { name: /Needs review 0/ }));
  expect(screen.getByText("Nothing needs review")).toBeTruthy();
});

test("a delayed poll cannot remove a newly created ticket", async () => {
  vi.useFakeTimers();
  let resolvePoll: (value: Response) => void = () => {};
  let reads = 0;
  mockQueue();
  const original = vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation((input, options) => {
    if (input === "/api/tickets" && options?.method === "GET") {
      if (++reads === 1)
        return Promise.resolve(
          response([{ ...ticket, status: "running", classification: null }]),
        );
      return new Promise((resolve) => {
        resolvePoll = resolve;
      });
    }
    return original(input, options);
  });
  await act(async () => {
    render(<App />);
  });
  await act(async () => {
    vi.advanceTimersByTime(2000);
  });
  fireEvent.click(screen.getByRole("button", { name: "New ticket" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Subject" }), {
    target: { value: "New request" },
  });
  fireEvent.change(screen.getByRole("textbox", { name: "Message" }), {
    target: { value: "Need access" },
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Create ticket" }));
  });
  await act(async () => {
    resolvePoll(response([ticket]));
  });
  expect(screen.getByRole("button", { name: "New request" })).toBeTruthy();
});
