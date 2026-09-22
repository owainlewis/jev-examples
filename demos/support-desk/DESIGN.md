---
name: Jev Support Desk
description: A white-and-green support inbox for exploring model decisions.
colors:
  green: "#1b5544"
  ink: "#203b34"
  muted: "#626f68"
  line: "#dde3dc"
  white: "#fffefa"
  canvas: "#f7f8f5"
  review-background: "#faf1dd"
  review-text: "#775813"
  error-background: "#f8e8df"
  error-text: "#883e25"
typography:
  body:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "14px"
  headline:
    fontSize: "26px"
    fontWeight: 650
    letterSpacing: "-0.7px"
rounded:
  control: "6px"
  segment: "8px"
  inbox: "10px"
---

# Design System: Jev Support Desk

## Overview

The approved composition is a compact three-panel inbox: queues, ticket list, and ticket detail. Warm white surfaces, dark green actions, fine dividers, and restrained status colors keep customer text and model results central. This records the built system in `frontend/src/style.css` and `frontend/src/App.tsx`, with product boundaries from `PRODUCT.md` and `docs/design.md`.

## Colors

Green identifies primary actions and type labels; ink carries main text, muted carries secondary explanations, and line separates surfaces. Pale green backgrounds identify selected queues and tickets. Amber marks review and reset confirmation; rust marks errors and urgency. Status always includes text. Team dots supplement named queues.

## Typography

Use the system sans stack above; Inter is preferred when available. Main headings are compact and slightly tightened. Ticket detail titles use 21px, decision headings 18px, customer text 13px with 1.85 line height, and supporting labels 10–12px. Counts, probabilities, confidence, and timing use tabular numerals. Code uses `ui-monospace, SFMono-Regular, Consolas, monospace` at 11px with 1.8 line height.

## Layout

The default shell has a 72px header, 224px queue sidebar, 300px ticket list, and flexible detail column. Main padding is 32px vertically and 30px horizontally; content panels use roughly 20–30px padding and controls use 8–16px gaps.

- At 1550px and wider, the list grows to 340px, main padding to 40px/48px, and detail side padding to 40px.
- At 1150px and below, sidebar/list widths become 185px/250px, padding tightens, the mode hint disappears, and the run action and explanation stack.
- At 900px and below, queues wrap above the inbox; the list remains beside detail at 240px. Sidebar identity and explanatory copy disappear.
- At 650px and below, list and detail stack. The list scrolls within 265px with a sticky heading; previews disappear. Four mode buttons share the full width. Detail padding is 20px horizontally; correction and reset controls wrap.

## Elevation & Depth

Depth comes from surface tones and one-pixel borders. Only the active mode segment has a small shadow (`0 2px 5px #203b3412`). Code blocks use a dark green surface. Avoid additional floating cards or decorative elevation.

## Shapes

Controls and code blocks use the control radius; segmented controls and the brand mark use the segment radius. The enclosing inbox uses the largest radius. Ticket rows meet flush against dividers. Small tags and meters use 3–4px corners.

## Components

Choice, Noul, Score, and Combined are pressed-state buttons in a labelled group. Switching modes does not send a request. **Run classification** is the explicit action: single modes preview answers without changing the queue; Combined displays four questions in one request and saves routing. Saved routing and manual decisions remain separate from model results.

Choice and Score show labelled distribution bars; Score also shows its weighted rubric score. Noul shows true/false percentages and a binary meter. Empty results invite a run without invented values. Pending results show explanatory text and a spinner; failures show a readable error. Questions, Python code, and raw responses use native expandable details.

Buttons have pale hover fills, darker green primary hover, and disabled opacity (0.55). Interactive elements have a 3px green focus outline with 3px offset. Forms use visible labels; queue navigation, ticket selection, and modes expose their states. Errors use alerts, notices use status announcements, and results use a polite live region with a busy state. Numeric text accompanies every chart. Mobile primary actions are at least 44px tall and mode buttons 40px. Reduced-motion preferences disable the spinner, answer reveal, and disclosure transitions.

## Do's and Don'ts

- Preserve the four-mode teaching sequence and visible distinction between previews, model answers, and routing policy.
- Keep labelled results and request status readable at desktop and mobile widths.
- Do not imply a refund flag authorizes a payment or fill empty states with simulated output.
- Keep technical details inside the existing expandable sections.

## Simplified inbox update

New tickets classify automatically on creation. The default result is compact: team, priority, refund intent, and any review reason. The mode selector, per-question distributions, and code/raw panels are behind Explore question types. Back to inbox restores Combined. Seed samples require an explicit classification so loading or resetting the app does not incur API calls.
