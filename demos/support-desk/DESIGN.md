# Ticket queue interface

Mode: operate. A single table presents request, department, priority, and status. New ticket opens an inline form above the table. The request button expands a second row containing its message and the two probability distributions. All tickets / Needs review are the only filters.

Inherit the existing warm-white and green system: background #f5f7f2, content #fffefa, text #233c32, action #205440, muted #637167, dividers #dce3d8. Native sans-serif typography; 30px desktop title, 13px table text, 11px probabilities. Numeric values use tabular numerals. Green marks accepted state, amber review and High, and rust Critical/failed. Text labels carry the meaning without relying on colour.

At widths below 1000px details stack. Below 650px, each table row becomes a labelled request block while retaining department/priority/status text. The inline form stacks its footer. Focus rings, native labels, button expanded/pressed states, error alerts, result status announcements, reduced motion, empty queue, and saved-ticket failures are implemented.

No sidebar, mode selector, refund/impact result, correction form, raw/code panels, reset control, or fabricated metrics. Both displayed percentages and review decisions come from category probabilities. Example selection fills the form without calling Jev.
