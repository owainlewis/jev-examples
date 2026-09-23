import { labels, percentage, themePolicy } from "./policy.mjs";

const $ = (id) => document.getElementById(id);
let config;
let result;
let busy = false;

function syncForm() {
  $("analyze").disabled =
    busy || !config?.configured || !$("feedback").value.trim();
  $("feedback").disabled = busy;
  $("example").disabled = busy || !config;
  $("clear").disabled = busy || !$("feedback").value;
  $("count").textContent =
    `${$("feedback").value.length.toLocaleString()} / 6,000`;
  $("output-pane").setAttribute("aria-busy", String(busy));
}

function clearResult() {
  result = null;
  $("results").hidden = true;
  $("empty-state").hidden = false;
  $("request-error").hidden = true;
  $("analyze").textContent = "Analyze feedback ↗";
  $("run-meta").textContent = "No analysis yet";
  $("run-status").textContent = "Analyze this feedback to see Jev’s reading.";
  syncForm();
}

function showPolicy() {
  const threshold = Number($("threshold").value);
  $("threshold-value").textContent = `${threshold}%`;
  $("threshold").setAttribute("aria-valuetext", `${threshold} percent`);
  if (!result) return;
  const review = themePolicy(result.theme.probability, threshold);
  $("policy-result").textContent = review
    ? `Review theme · ${percentage(result.theme.probability)} is below ${threshold}%.`
    : `Theme passes your rule · ${percentage(result.theme.probability)} meets ${threshold}%.`;
  $("policy-result").className = review ? "review" : "passes";
}

function bars(target, entries) {
  target.replaceChildren();
  for (const [label, value] of entries) {
    const row = document.createElement("div");
    row.className = "distribution-row";
    const heading = document.createElement("div");
    const name = document.createElement("span");
    name.textContent = label;
    const number = document.createElement("span");
    number.textContent = percentage(value);
    heading.append(name, number);
    const bar = document.createElement("progress");
    bar.max = 1;
    bar.value = value;
    bar.setAttribute("aria-label", `${label} probability`);
    row.append(heading, bar);
    target.append(row);
  }
}

function renderResult() {
  $("empty-state").hidden = true;
  $("results").hidden = false;
  $("theme-value").textContent = labels[result.theme.choice];
  $("theme-probability").textContent =
    `${percentage(result.theme.probability)} probability`;
  bars(
    $("theme-bars"),
    Object.entries(result.theme.probabilities).map(([key, p]) => [
      labels[key],
      p,
    ]),
  );
  $("actionable-value").textContent = percentage(result.actionable.probability);
  bars($("actionable-bars"), [
    ["Yes", result.actionable.probability],
    ["No", 1 - result.actionable.probability],
  ]);
  $("impact-value").textContent = result.impact.score.toFixed(2);
  bars(
    $("impact-bars"),
    [
      "0 · No blockage stated",
      "1 · Slowed / workaround",
      "2 · Blocked / no workaround",
    ].map((label, index) => [label, result.impact.probabilities[index]]),
  );
  $("run-meta").textContent =
    `${result.model} · ${(result.elapsed_ms / 1000).toFixed(2)} s`;
  $("run-status").textContent =
    "Analysis complete. Three answers from one live Jev request.";
  showPolicy();
  $("output-title").focus({ preventScroll: true });
}

async function connect() {
  $("reconnect").hidden = true;
  $("setup-error").hidden = true;
  try {
    const response = await fetch("/api/config", {
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw new Error("Connection failed");
    config = await response.json();
    $("connection").textContent = config.configured
      ? `${config.model} · Key configured`
      : "API key needed";
    $("example").replaceChildren(new Option("Choose an example…", ""));
    config.examples.forEach((example, index) =>
      $("example").add(new Option(example.name, index)),
    );
    $("rubrics").replaceChildren();
    for (const [name, question] of Object.entries(config.questions)) {
      const section = document.createElement("section");
      const title = document.createElement("h3");
      title.textContent = `${name[0].toUpperCase()}${name.slice(1)} · ${question.type}`;
      const instructions = document.createElement("p");
      instructions.textContent = question.instructions;
      const list = document.createElement("dl");
      for (const [key, value] of Object.entries(question.criteria)) {
        const term = document.createElement("dt");
        term.textContent = key;
        const definition = document.createElement("dd");
        definition.textContent = value;
        list.append(term, definition);
      }
      section.append(title, instructions, list);
      $("rubrics").append(section);
    }
    if (!config.configured) {
      $("setup-error").textContent =
        "Add TYPESAFE_API_KEY to the demo’s .env file, restart the server, then reconnect. You can explore the examples while you set up.";
      $("setup-error").hidden = false;
      $("reconnect").hidden = false;
    }
  } catch {
    config = null;
    $("connection").textContent = "Server unavailable";
    $("setup-error").textContent =
      "Could not connect to the local server. Start it using the README, then reconnect. Your draft is still here.";
    $("setup-error").hidden = false;
    $("reconnect").hidden = false;
  }
  syncForm();
}

$("feedback").addEventListener("input", () => {
  $("example").value = "";
  $("example-hint").textContent =
    "Your own wording. Only the text below is sent to Jev.";
  clearResult();
});
$("example").addEventListener("change", () => {
  const example = config.examples[$("example").value];
  if (!example) return;
  $("feedback").value = example.text;
  $("example-hint").textContent = example.hint;
  clearResult();
});
$("clear").addEventListener("click", () => {
  $("feedback").value = "";
  $("example").value = "";
  $("example-hint").textContent =
    "Examples fill the editor. They do not call Jev.";
  clearResult();
  $("feedback").focus();
});
$("threshold").addEventListener("input", showPolicy);
$("reconnect").addEventListener("click", connect);
$("feedback-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy || !config?.configured || !$("feedback").value.trim()) return;
  clearResult();
  busy = true;
  syncForm();
  $("analyze").textContent = "Analyzing…";
  $("run-status").textContent =
    "Jev is reading your feedback. Waiting for three answers…";
  $("run-meta").textContent = "Request in progress";
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Demo-Request": "feedback-lens",
      },
      body: JSON.stringify({ feedback: $("feedback").value }),
      signal: AbortSignal.timeout(45000),
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(data.detail || "The request failed. Please retry.");
    result = data;
    renderResult();
    $("analyze").textContent = "Analyze again ↗";
  } catch (error) {
    $("request-error").textContent =
      error.name === "TimeoutError" || error instanceof TypeError
        ? "The server did not respond. Your text is still here. Check the connection and retry. A timed-out request may still count toward API usage."
        : error.message;
    $("request-error").hidden = false;
    $("analyze").textContent = "Retry analysis ↗";
    $("run-meta").textContent = "Analysis failed";
    $("run-status").textContent =
      "No result returned. Your feedback is ready to retry.";
  } finally {
    busy = false;
    syncForm();
  }
});

connect();
