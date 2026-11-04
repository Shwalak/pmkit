# How pmkit works (plain English)

The explanation I would give a PM, an engineer or an interviewer who asks "what does this do, and why should I trust it?"

## The A/B readout

You give it the result of a finished test: conversions and visitors for control and treatment. It returns a reading in plain language, with the numbers behind it.

| Output | What it means |
|---|---|
| **Difference** (in percentage points) and **relative lift** | The size of the gap. 10% to 12% is +2 pp and a +20% relative lift. Both are shown because each is easy to misread alone. |
| **p-value** | If there were truly no difference, how often would random noise alone produce a gap this large or larger? A small value says "unlikely to be noise". It is **not** the probability that the treatment works. |
| **Interval** | The range of differences consistent with the data. If the whole range is above zero, the treatment is better; if it straddles zero, the data cannot tell. The width shows how precisely you measured. |
| **Split check** | Whether visitors were divided between arms as planned. |
| **Smallest detectable effect** | How small a real improvement this test could have reliably noticed. |

### Why the interval is built the way it is

The textbook "difference plus or minus 1.96 standard errors" interval misbehaves with small counts or rates near 0% or 100%: it can say the true difference might be beyond +100%. pmkit uses **Newcombe's method**, which combines two Wilson score intervals and stays sensible in those cases. Wilson and Newcombe are standard; the work was implementing them correctly and checking them (see [validation.md](validation.md)).

### The check that overrides everything: sample ratio mismatch

If you planned a 50/50 split and got 5,000 vs 5,400, something is wrong with how users were assigned or counted (bots, a redirect that drops people, a logging bug). The chi-square test flags this. When it fires, **pmkit refuses to give a verdict**, because every downstream number rests on a broken assignment. A "significant" result on broken data is the most dangerous kind.

### How the verdict is decided

| Situation | Reading |
|---|---|
| Split looks broken | **Do not trust this result.** Overrides everything. |
| p below alpha and the interval excludes zero | Significantly better (or worse). |
| p below alpha but the interval includes zero | **Borderline.** The two disagree; treat as inconclusive. This is a real case near the threshold, not a bug. |
| Otherwise | **Inconclusive.** States the smallest effect the test could reliably detect and says it is *not* evidence of no effect. |

That last row matters most. "No significant difference" from an underpowered test mostly means "we could not tell". The tool says so in words, with the number.

### Planning before the test

`pmkit ab size` answers "how many visitors do I need?" for a baseline rate and the smallest change worth detecting, and `pmkit ab mde` answers the reverse ("what can my traffic detect?"). Deciding the sample size **before** starting is the single most useful habit, and the CLI repeats it.

### What the readout cannot protect you from

It prints these assumptions with every result: the sample size was fixed in advance, you looked once, this is one primary metric, and each user appears once. **Peeking** at a running test and stopping when it looks good, **testing many metrics** and reporting the winner, and **repeat users** all make the p-value look better than it is. None are detected; they are habits, not calculations.

## The PRD checker

It reads a Markdown PRD, splits it into sections (including bold label lines used as sub-headings) and runs checks a careful reviewer would run in the first five minutes:

| Check | Catches |
|---|---|
| Required sections | No problem, users, goals, non-goals, success metrics, requirements or risks |
| Empty sections | A heading with nothing under it |
| Metrics have numbers | "We will know it worked when users are happy" |
| Guardrail present | A primary metric with nothing that must not get worse |
| Risks have mitigations | A list of worries with no plan |
| Vague words | "fast", "intuitive", "better", "improve" with no measure, in goals, metrics and requirements |
| Placeholders | `TBD`, `TODO`, `[insert ...]` left in |

What it **cannot** do is say whether the PRD is any good. A document can pass every check and describe a pointless product. It removes cheap-to-catch problems so that a reviewer's attention goes to the hard ones.

### Three bugs I found by testing it on real documents

I ran the checker on two PRDs I had written earlier. It flagged two real gaps (no guardrail metric; no stated primary metric), which I fixed. Building and using it also exposed three flaws in the checker itself, each fixed with a regression test:

1. **Digits in unfilled placeholders counted as numbers.** A template line like `baseline [value or "unknown, measured in week 1"]` contains a "1", so metrics with no real numbers passed.
2. **List numbering counted as numbers.** `1. A fast, intuitive form` looked quantified.
3. **"Success" was not recognised as a metrics heading**, a very common one.

All three were false negatives, the worse kind for a checker: it said "fine" when it was not.

## Questions to be ready for

- *"Is a p-value of 0.03 the chance the treatment works?"* No. It is how surprising the data would be if there were no effect.
- *"We saw no significant difference, so can we say it does nothing?"* No. Check the smallest detectable effect. Underpowered tests cannot rule out effects they were never able to see.
- *"Why does it sometimes refuse to give a verdict?"* A sample ratio mismatch means the experiment's data is unsound. Fix assignment first.
- *"How do you know the maths is right?"* It is tested against scipy and statsmodels on 500 random cases (agreement to about 1e-16), and a 40,000-simulation Monte Carlo confirms the sample sizes deliver 80% power and a 5% false-positive rate. See [validation.md](validation.md).
- *"Why no dependencies?"* The statistics need only the normal distribution, which the standard library provides. Fewer moving parts and nothing to break.
- *"What would you build next?"* Continuous metrics (revenue per user), sequential testing so early looks are valid, and a way to evaluate the prompts systematically.

## Where to look in the code

| If you want to understand | Read |
|---|---|
| How a verdict is decided | `readout()` in `pmkit/abtest.py` |
| The interval and tests | `newcombe_difference_ci`, `two_proportion_z`, `sample_ratio_mismatch` in `pmkit/abtest.py` |
| What the PRD checker looks for | the constants at the top of `pmkit/prd.py` and `check_prd()` |
| How outputs stay honest | `tests/test_examples_current.py` |
