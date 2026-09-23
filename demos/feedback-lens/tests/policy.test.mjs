import assert from "node:assert/strict";
import test from "node:test";
import { percentage, themePolicy } from "../frontend/policy.mjs";

test("theme rule includes equality and uses the unrounded probability", () => {
  assert.equal(themePolicy(0.8, 80), false);
  assert.equal(themePolicy(0.79999, 80), true);
  assert.equal(themePolicy(0.81, 80), false);
  assert.equal(themePolicy(0.81, 90), true);
  assert.equal(themePolicy(1, 100), false);
  assert.equal(themePolicy(0.5, 50), false);
});

test("probability formatting retains one decimal place", () => {
  assert.equal(percentage(0), "0.0%");
  assert.equal(percentage(1), "100.0%");
  assert.equal(percentage(0.12345), "12.3%");
});
