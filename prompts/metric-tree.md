# Metric tree

**Use it for:** breaking a goal into the metrics that drive it, finding the leading and lagging ones, and spotting how each can be gamed.
**Do not use it for:** choosing targets. It never knows your baselines.
**Status:** drafted, not systematically evaluated.

## What you provide

- The goal in one sentence, the product or funnel it applies to, and who the users are.
- Anything you already measure.

## The prompt

```text
You are helping me design a metric tree. First decide whether you have enough information.

Step 1. If the goal, the user, or the funnel is unclear, ask me up to 5 clarifying questions and STOP.
Do not produce the tree until I answer.

Step 2. Otherwise produce:
1. A tree from the goal down to the behaviours that drive it (3 levels at most).
2. For each metric: a precise definition (numerator, denominator, time window), whether it is leading or lagging,
   and where the data would come from.
3. For each metric: how it could be gamed or misread (Goodhart risk).
4. Two to four guardrail metrics: what must NOT get worse while the primary metric improves.
5. A list of metrics the tree needs that I do not seem to measure today (instrumentation gaps).

Rules:
- Never invent baselines, benchmarks or targets. If a number is needed, write "baseline: unknown" and say how to find it.
- Mark every assumption as ASSUMPTION.
- Prefer few metrics. If a metric would not change a decision, leave it out and say so.
- Do not recommend vanity metrics (raw page views, sign-ups with no activation) as primary metrics.

GOAL:
{goal}

PRODUCT / FUNNEL:
{description}

CURRENTLY MEASURED:
{metrics, or "unknown"}
```

## Check the output

- For each metric, can you write the SQL or the spreadsheet formula? If not, the definition is too vague.
- Does any metric have a number in it that you did not supply? Remove it.
- Is there at least one guardrail? If not, ask for one.

## Known failure modes

- **Plausible-looking benchmarks.** The prompt forbids them; check anyway.
- **Too many metrics.** Trees tend to sprawl; cut anything that would not change a decision.
- **Confusing outputs with outcomes** (shipping a feature versus users getting value).
