# Ticket queue interface

Mode: operate. A single table presents request, department, priority, and status. New ticket opens an inline form above the table. The request button expands a second row containing its message and the two probability distributions. All tickets / Needs review are the only filters.

Use React with official shadcn/ui Button, Badge, Input, Textarea, and NativeSelect components, generated into frontend/src/components/ui. Tailwind CSS v4 provides component utilities; style.css holds the queue layout and neutral theme. components.json configures the registry and @ aliases for future additions.

The minimalist palette uses background #fafafa, content #ffffff, text/action #18181b, muted #71717a, and dividers #e4e4e7. Native sans-serif typography; 32px desktop title, 13px table text, 11px probabilities. Header and main share a 1200px alignment grid. Numeric values use tabular numerals. Green marks accepted state, amber review and High, and red Critical/failed. Text labels carry meaning without relying on colour. Segmented filters, generous row spacing, and subtle borders keep the queue scannable.

At widths below 1000px details stack. Below 650px, each table row becomes a labelled request block while retaining department/priority/status text. The inline form stacks its footer. Focus rings, native labels, button expanded/pressed states, error alerts, result status announcements, reduced motion, empty queue, and saved-ticket failures are implemented.

No sidebar, mode selector, refund/impact result, correction form, raw/code panels, reset control, or fabricated metrics. Both displayed percentages and review decisions come from category probabilities. Example selection fills the form without calling Jev.
