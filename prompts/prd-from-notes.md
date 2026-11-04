# PRD from messy notes

**Use it for:** a first draft of a PRD from meeting notes, tickets and research, with the gaps made visible instead of papered over.
**Do not use it for:** the final PRD. A draft that reads well can still be wrong; every UNKNOWN is your to-do list.
**Status:** drafted, not systematically evaluated.

## What you provide

- Your notes, tickets, research snippets or a rough brain-dump.
- The template: run `pmkit prd new --title "..."` and paste the result, or use `pmkit/prd_template.md`.

## The prompt

```text
Draft a PRD from the notes below, using exactly the sections in the template I give you.

Rules:
1. Use ONLY facts that appear in my notes. Do not invent users, numbers, quotes, dates, competitors or evidence.
2. Where the notes do not say something the template needs, write:
   UNKNOWN: <the specific question> (ask: <who is likely to know>)
   Do not fill the gap with a plausible guess.
3. Label anything that is your suggestion rather than something in the notes as PROPOSAL.
4. Success metrics: give a primary metric and at least one guardrail. For baselines and targets that are not in
   the notes, write UNKNOWN; do not propose numbers.
5. Non-goals: list only things that the notes suggest are tempting scope. If none, write UNKNOWN.
6. Keep it short. Prefer one clear sentence to three vague ones. Avoid words like "seamless", "intuitive",
   "better" and "improve" unless attached to a measure.
7. End with a section "What I assumed or could not tell" listing every UNKNOWN in one place.

TEMPLATE:
{paste template}

NOTES:
{paste notes}
```

## After the draft

1. Save it as `prd.md` and run `pmkit prd check prd.md`. Fix every failure.
2. **Passing the checker does not mean the PRD is good.** It checks structure and common omissions, nothing about whether the problem is real or the metric is right.
3. Resolve each `UNKNOWN`, then delete the marker. Anything still unresolved moves to "Open questions".

## Known failure modes

- **Confident gap-filling.** Models like to complete a template. The UNKNOWN rule fights this; scan for specific-sounding numbers or user names that you cannot find in your notes.
- **Generic problem statements** that could describe any product. Ask: could a competitor paste this unchanged?
- **Requirements that restate the goal** rather than say what the product does.
