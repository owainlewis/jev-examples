# Trading simulator interface

The supplied screenshot is the visual reference: light background, large price chart on the left, compact policy and probabilities on the right, and a decision feed. Reuse the repository's React and shadcn button conventions.

Use an off-white page, white working surface, muted green buy labels, muted red sell labels, and tabular numbers. Colour is accompanied by action text. The screenshot's forced buy/sell policy is not adopted; Hold is required. Claims about profits and latency must come from actual state.

On narrow screens, put the chart before the policy and decision sections. Keep the feed horizontally scrollable. Show empty, disconnected, missing-key, warming-up, paused, running, and API-error states. Mode switches reset the virtual portfolio only after confirmation. Start is explicit because it spends TypeSafe credit.
