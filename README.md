# pmkit

**A small, tested toolkit for product managers: read A/B tests honestly, plan sample sizes, and catch the obvious holes in a PRD.**

Zero dependencies. Standard-library Python 3.10+.

## Why this exists

Three things go wrong in product work again and again, and they are cheap to prevent:

- **A/B tests get read badly.** "Not significant" gets taken as "no effect", a broken traffic split goes unnoticed, and nobody planned the sample size.
- **PRDs ship with predictable holes**: no non-goals, a success metric with no number, a risk with no mitigation.
- **Prompts for PM work live in someone's notes**, with no checks and no record of where they fail.

pmkit is a small answer to each, built so that every claim it makes is verifiable.

## What is inside

| Part | What it does |
|---|---|
| `pmkit ab readout` | Reads a finished two-arm test: difference, p-value, Newcombe interval, a sample-ratio-mismatch check, and a plain-language verdict that says when a result is inconclusive or untrustworthy |
| `pmkit ab size` and `pmkit ab mde` | How many visitors a test needs, and the smallest effect your traffic can detect |
| `pmkit prd check` | Checks a Markdown PRD for missing sections, metrics with no numbers, vague words, unfinished placeholders and more |
| `pmkit prd new` | A PRD template that the checker will flag until you finish it |
| [`prompts/`](prompts/) | Three Claude prompts (interview synthesis, metric tree, PRD from notes), each with an output checklist and known failure modes |

## Quickstart

```bash
git clone https://github.com/Shwalak/pmkit.git
cd pmkit
pip install -e .
pmkit ab readout --control 200/1000 --treatment 240/1000
```

## See it work

All output below is real. It is regenerated and compared by a test, so it cannot drift from what the code prints (`tests/test_examples_current.py`).

**A clear win**, `pmkit ab readout --control 200/1000 --treatment 240/1000`

```text
A/B test readout (two arms, yes/no metric)

              visitors  conversions     rate
  control        1,000          200   20.00%
  treatment      1,000          240   24.00%

Difference:   +4.00 pp   (relative lift +20.0%)
95% interval: +0.37 pp to +7.62 pp
p-value:      0.0308   (pooled two-proportion z-test, two-sided)
Split check:  ok   (sample ratio mismatch p = 1)

Reading: Treatment is statistically better than control: +4.00 pp (95% CI: +0.37 pp to +7.62 pp, p = 0.0308).

Valid if: the sample size was fixed in advance, you looked at the data once, this is the one primary
metric, and each user appears once. Peeking early, testing many metrics or repeat users make the
p-value look better than it is.
```

**A result that looks like a big win but is not trustworthy**, `pmkit ab readout --control 500/5000 --treatment 700/5400`

```text
A/B test readout (two arms, yes/no metric)

              visitors  conversions     rate
  control        5,000          500   10.00%
  treatment      5,400          700   12.96%

Difference:   +2.96 pp   (relative lift +29.6%)
95% interval: +1.74 pp to +4.18 pp
p-value:      0.0000   (pooled two-proportion z-test, two-sided)
Split check:  ALERT   (sample ratio mismatch p = 8.77e-05)

Reading: Do not trust this result. The split of visitors between arms looks wrong (sample ratio mismatch, p = 8.8e-05). Find out why before reading anything else.

Valid if: the sample size was fixed in advance, you looked at the data once, this is the one primary
metric, and each user appears once. Peeking early, testing many metrics or repeat users make the
p-value look better than it is.
```

The treatment looks 30% better and is "highly significant", yet the tool refuses to call it. The planned 50/50 split came out 5,000 vs 5,400, which points to a broken assignment, so nothing else on the page can be trusted.

**A weak PRD**, `pmkit prd check examples/prds/weak-example.md`

```text
PRD check: examples/prds/weak-example.md  (65 words)

  FAIL           [section] No problem section found.
  FAIL           [section] No users section found.
  FAIL           [section] No goals section found.
  FAIL           [section] No non-goals section found.
  FAIL           [section] No risks section found.
  FAIL  line 12  [metrics] Success metrics contain no numbers. State a baseline and a target (or say explicitly that the baseline is unknown).
  WARN           [section] No open questions section found.
  WARN           [section] No rollout section found.
  WARN           [length] Only 40 words. Too thin to align a team.
  WARN  line 5   [placeholder] Unfinished placeholder "TBD".
  WARN  line 8   [vague] "Fast" with no measure: "Fast charts"
  WARN  line 9   [vague] "Intuitive" with no measure: "Intuitive filters"
  WARN  line 10  [vague] "Improve" with no measure: "Improve the user experience"
  WARN  line 12  [metrics] No guardrail metric mentioned: what must not get worse while the primary metric improves?
  (2 checks passed; use --verbose to list them)

Result: 6 fail, 8 warn, 2 pass
This checks structure and common omissions. It cannot tell you whether the PRD is any good.
```

## I ran it on my own PRDs

I used the checker on two PRDs I had written for other projects (a launch-readiness evals tool and a Google Ads product teardown). It found two real gaps:

| PRD | Finding | Fix |
|---|---|---|
| Evals tool | No guardrail metric: nothing said what must not get worse | Added the guardrail its tests already enforce |
| Google Ads teardown | No success metrics of its own, only a link to a companion document | Added a Success metrics section |

Both now pass. Building the checker also exposed three flaws in the checker itself (all false negatives), each fixed with a regression test. The story is in [docs/how-it-works.md](docs/how-it-works.md).

## How I know the statistics are right

The statistics are validated three ways ([docs/validation.md](docs/validation.md)):

1. Unit tests pinned to values from scipy and statsmodels.
2. Agreement with those libraries on 500 random experiments, to about 1e-16.
3. A seeded Monte Carlo simulation (40,000 tests per row) confirming that the sample sizes pmkit computes really deliver **80% power** and a **5% false-positive rate**.

Run it yourself: `pip install -e . scipy statsmodels numpy && python scripts/validate_against_references.py`

## Product tradeoffs

| Decision | Chose | Gave up | Why |
|---|---|---|---|
| Verdict wording | Plain language with the number behind it | Just a p-value | A PM needs "inconclusive, and here is the smallest effect this test could see", not a decimal |
| Broken traffic split | Refuse to give a verdict | Always showing a result | A significant result on broken assignment is worse than none |
| Interval | Newcombe (Wilson-based) | The simple formula | Stays valid with small counts and extreme rates |
| PRD checker | Deterministic rules | An LLM reviewer | Repeatable, free, runs in CI, and I can say exactly what it checks. It cannot judge quality, and says so. |
| Prompts | A few, with checks and failure modes | A large template library | A prompt without a way to check its output is a liability |
| Dependencies | None | Convenience libraries | Easy to install and audit; the standard library covers the maths |

## Limitations

- **Two arms, yes/no metrics only.** No revenue-per-user (continuous) metrics, no more than two variants.
- **No sequential testing.** Peeking at a running test invalidates the p-value, and pmkit cannot detect that you did.
- **No multiple-comparison correction.** If you test several metrics, adjust alpha yourself.
- **Assumes independent users.** Repeat users make the real uncertainty larger than reported.
- **The PRD checker finds omissions, not quality.** A PRD can pass every check and still be bad. Its heading recognition is English-only and heuristic, so unusual headings can be missed.
- **The prompts have not been systematically evaluated.** They are drafts with checks, not benchmarked tools. See below.

## Evaluating the prompts

I have not measured how well the prompts work, and I do not want to imply otherwise. The honest way to do it: write a set of realistic inputs with known right answers (for example, interview notes where I know a quote is absent, to see if it gets invented), define hard gates (no fabricated quotes, no invented numbers) and soft gates, run candidate prompts and compare. That is the approach in my ShipGate project, and applying it here is the first next step.

## Next steps

1. Evaluate the prompts with a ShipGate-style harness.
2. Continuous metrics (means and ratios) and the right interval for them.
3. Sequential testing, so early looks are valid.
4. A CI action that runs `pmkit prd check` on pull requests.
5. Multi-arm tests with a correction for multiple comparisons.

## Repository layout

```
pmkit/        abtest.py (statistics), prd.py (checker), cli.py, prd_template.md
prompts/      three Claude prompts with checks and failure modes
examples/     example PRDs, commands.json, and their real outputs
docs/         how-it-works.md (plain English), validation.md (how the maths is checked)
scripts/      validation against scipy/statsmodels; regenerate example outputs
tests/        unit tests, plus a test that keeps the example outputs current
```

Run the tests with `pip install -e ".[dev]" && pytest`.

## About

Designed and specified by Saksham as an AI and technical product manager portfolio project. The checks, the verdict rules and the decisions about what to refuse to say are the product thinking; the tests and the validation are the evidence it works.

## License

MIT
