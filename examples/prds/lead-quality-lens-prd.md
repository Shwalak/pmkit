# 5. PRD: Lead Quality Lens (concept)

**Author:** Saksham · **Status:** concept for discussion · **As of:** 2026-11-04

> This is an independent product concept written from public information. It is not Google's roadmap, I have no inside knowledge of Google's plans, and the name "Lead Quality Lens" is mine. Several assumptions below could be wrong; the ones I know about are listed in section 11 and tested in [07](07-interview-guide.md). I have not run user research for this document.

## 1. Summary

B2B advertisers increasingly hand targeting, creative and bidding to automation, but judge it on conversions that are often form fills. Google has built much of the plumbing to send later-stage outcomes back (see [2](02-what-google-shipped.md)), yet an advertiser still has no easy, trustworthy way to **see which parts of their spend produce qualified leads, and how sure the data is**. The Lead Quality Lens is a report that shows cost per qualified lead by search term, match source, asset, landing page and channel, flags where spend is not producing qualified leads, and is explicit about what is still too early or too thin to judge.

## 2. Problem

Evidence and counter-evidence are in [3](03-user-problems.md). The three problems this PRD targets:

- **P1:** optimising to form fills attracts low-quality leads (Medium confidence).
- **P2:** deep-funnel B2B signals are sparse and slow; the 63-day and 90-day upload windows mean some outcomes can never be attributed (Medium-high on structure).
- **P3:** hard to see quality by segment inside automated campaigns (**low-medium; needs validation**, and the thing most likely to make this PRD wrong).

## 3. Users and jobs

| User | Job |
|---|---|
| In-house B2B marketer | "Show me which of my spend produces qualified conversations, in a form I can defend to sales." |
| Agency PPC manager | "Tell me which accounts and segments need attention this week, without me building a report for each." |
| Sales or RevOps partner | "Make sure the ad account is using the definition of qualified that we actually use." |

## 4. Goals and non-goals

**Goals**
1. Make quality *visible* by segment without manual report joins.
2. Be honest about uncertainty: never present a noisy rate as a fact.
3. Turn evidence into a *suggested* next step the advertiser can accept or ignore.
4. Pull more advertisers toward supplying downstream stage data (activation).

**Non-goals**
- Automatically pausing, excluding or re-bidding anything. The Lens advises; the advertiser decides.
- Replacing the CRM, or defining "qualified" for the advertiser.
- Changing how Smart Bidding works.
- Individual-level lead data. The Lens uses aggregated conversion data already in the account.

## 5. Solution concept

### 5.1 Phases (sequenced by the RICE ranking in [4](04-opportunities-and-prioritization.md))

| Phase | Scope | Why this order |
|---|---|---|
| **0. Activation** | A readiness check inside the account: is a downstream stage mapped and categorised, are click IDs and hashed data being captured, are uploads arriving inside the 63/90-day windows? Each gap links to the fix. | Cheap, broad, and the prerequisite. Without stage data there is nothing to show. |
| **1. Lens MVP** | The quality report for Search and AI Max by search term and match source, plus asset and landing page; maturity handling; evidence labels; a plain-language summary. | The core value. |
| **2. Intelligence** | Performance Max channel breakdown, suggested actions (negative keyword, test a holdout, review a landing page), alerts on sudden quality drops. | Needs Phase 1 evidence on what users trust and act on. |

### 5.2 Core definitions

- **Qualified:** the advertiser's own mapped stage (for example, a conversion action categorised as "Qualified lead"). The Lens never redefines it; it warns if the mapping looks unstable (see R9).
- **Cohort:** leads grouped by the month of the click, so quality is compared like for like.
- **Resolved vs pending:** a lead is *resolved* once it is older than the point by which most leads in that account have reached or missed the qualified stage; otherwise *pending*. This maturity point is estimated from the account's own history and is capped by the **63-day** attribution limit for enhanced conversions for leads. Leads that qualify after the limit **cannot be matched** and are reported as unattributable, not as failures.
- **Evidence level per segment:** *Enough*, *Thin* or *Too early*, from resolved lead count and the width of the uncertainty interval.

### 5.3 Concept sketch

*Layout illustration only. Every number below is invented to show structure; none is real data.*

**Search terms, last 90 days (clicks cohort), stage: Qualified lead**

| Segment | Spend | Raw leads | Qualified (resolved) | Pending | Cost / qualified | Qualified rate (80% interval) | Evidence |
|---|---|---|---|---|---|---|---|
| "…software pricing" (exact) | high | many | many | few | low | high, narrow | Enough |
| "…free template" (AI Max, broad) | high | many | almost none | few | n/a | low, narrow | Enough: **quality leak** |
| "…alternative to X" (AI Max, broad) | low | few | some | many | n/a | wide | Too early |

Below the table: *"Two segments account for the largest share of spend with almost no qualified leads after the usual qualification time. One is expanded matching. Consider a negative keyword or a holdout test before cutting: average quality is not the same as marginal value."*

### 5.4 How the numbers are produced

- Qualified rate per segment is estimated with a **Beta-binomial model that shrinks small segments toward their campaign average**, so a segment with 3 leads and 2 qualified is not shown as "67%". Intervals are shown, not point estimates alone.
- **Pending leads** are modelled with the account's own time-to-qualify distribution so recent cohorts are not penalised for being young.
- Segments are ranked by **expected spend at risk** (spend multiplied by the probability that the true qualified rate is below the account's threshold), not by raw rate, so noise does not float to the top.
- Segments below a minimum resolved-lead count are shown as *Too early* and are never flagged.

### 5.5 Plain-language summaries

A model may write the summary sentences, with one hard rule: **every number in the text must come from the computed table**. Numbers are inserted programmatically, and the summary is checked before display; if any figure does not match, the summary is dropped and the table stands alone. This is the kind of feature I would gate before launch with explicit evals (hard gate on factual consistency, soft gates on helpfulness and length), the approach in my ShipGate project.

## 6. Requirements

| ID | Requirement | Priority |
|---|---|---|
| R1 | Show spend, raw leads, resolved qualified leads, pending leads and cost per qualified lead by search term, match source, asset, final URL and channel | P0 |
| R2 | Let the advertiser choose which mapped stage counts as "qualified" per campaign | P0 |
| R3 | Show uncertainty (interval) and an evidence label for every segment | P0 |
| R4 | Separate *pending* from *resolved* leads, and mark leads outside the attribution window as *unattributable* | P0 |
| R5 | Rank by expected spend at risk; never flag *Too early* segments | P0 |
| R6 | Phase 0 readiness check with links to fixes | P0 |
| R7 | Label every view "average quality, not marginal value", and offer a holdout experiment before any cut | P1 |
| R8 | Template-based summaries with number-consistency checks | P1 |
| R9 | Warn when the qualified stage's definition or volume shifts abruptly (possible mapping change or stage inflation) | P1 |
| R10 | Performance Max channel breakdown | P2 |
| R11 | Alerts for sudden drops in qualified rate | P2 |
| R12 | Exportable report for sales and RevOps | P2 |

**Non-functional:** results update at least daily; no view claims precision the data cannot support; all thresholds are visible in the UI.

## 7. Success metrics

Design, sample-size reasoning and decision rules are in [6](06-metrics-and-experiment-plan.md). The measures:

- **Primary, leading: evidence-backed action rate.** The share of Lens-active accounts that act on a flagged segment within 14 days of first seeing it.
- **Primary, lagging: cost per qualified lead on resolved cohorts**, treatment versus control, read only on click cohorts older than the account's maturity point (bounded by the 63-day attribution limit).
- **Activation:** the share of eligible accounts that complete Phase 0 (stage mapped, uploads healthy).
- **Guardrails:** qualified lead volume per account must not fall versus control by more than a margin fixed before launch; total spend per account must not drop sharply (a sign of over-cutting); few actions taken during a learning period; and a low rate of "this looks wrong" feedback and summary-consistency failures.
- **Baselines are unknown.** None exist yet. The first cohort establishes them, and targets are set from that before any launch.

## 8. Key decisions and tradeoffs

| Decision | Chose | Gave up | Why |
|---|---|---|---|
| Advise vs act | Suggest only | Auto-pause or auto-exclude | Acting on noisy data could damage a campaign; Google's own guidance warns about disturbing learning phases. Trust has to be earned first. |
| Rank by | Expected spend at risk | Raw lowest rate | Raw rate is dominated by tiny segments. |
| Small segments | Shrink toward the average and say "Too early" | Showing every number | A confident wrong number is worse than a blank. |
| Definition of qualified | Advertiser's own mapped stage | A Google-defined standard | The advertiser's sales process is the source of truth; imposing a definition would break trust. |
| Aggregation | Segment-level aggregates | Lead-level views | Avoids new privacy surface and matches existing reporting. |
| Language | Templated, number-checked | Free-form generated text | Hallucinated figures in a decision tool would be a trust-destroying failure. |

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Overreaction to noise** | Shrinkage, intervals, minimum counts, ranking by spend at risk |
| **Average vs marginal:** cutting a low-average segment may hurt overall results | Labelled in every view; suggest a holdout first (cites Google's own caution on average channel returns) |
| **Right-censoring:** young leads look like failures | Pending/resolved separation; cohorts |
| **Unattributable outcomes** after 63/90 days | Reported as unattributable; surfaced in Phase 0 so advertisers know their blind spot |
| **Goodhart:** optimising a campaign to the Lens's stage may inflate that stage | R9 warning; cross-check against a later stage where available |
| **Definition drift** between marketing and sales | Phase 0 prompts stage review; R9 |
| **Hallucinated numbers in summaries** | Programmatic insertion and a consistency gate |
| **Interference with learning** if users act too soon | Suggested-action copy references learning periods |

## 10. Dependencies

- Stage data arriving via enhanced conversions for leads or offline import (Data Manager API since June 2026).
- Conversion action categories being set correctly.
- Reporting access by search term, asset, final URL and (Phase 2) channel.

## 11. Open questions and assumptions that could sink this

1. **Does a default quality-adjusted view already exist or is it planned?** (Most important. I could not confirm either way.)
2. Do enough B2B accounts have *any* downstream stage data to make the Lens useful? If not, activation is the real product.
3. Is the manual workaround (segment by conversion action, join with cost) painful enough that advertisers would use a Lens?
4. Do B2B volumes support the statistics, or will most segments read *Too early*?
5. Would advertisers act on suggestions, or only read them?
6. Is "qualified" defined consistently enough to build on (P6)?

## 12. Rollout and kill criteria

1. **Validate** with interviews first ([07](07-interview-guide.md)).
2. **Phase 0** to a small cohort of accounts with stage data; measure activation.
3. **Phase 1** as an opt-in beta; run the experiment in [6](06-metrics-and-experiment-plan.md).
4. **Kill or re-scope** if: interviews show a readiness diagnostic alone drives most of the behaviour (ship that, shelve the Lens); most target accounts read *Too early* on most segments; or users view the report but take no action after a full cycle.

Next: [6. Metrics and experiment plan](06-metrics-and-experiment-plan.md)
