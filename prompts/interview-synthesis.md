# Interview synthesis

**Use it for:** turning raw notes from user interviews into evidence you can act on, without letting the model smooth over contradictions or invent quotes.
**Do not use it for:** deciding what to build. It organises evidence; the judgment stays with you.
**Status:** drafted, not systematically evaluated.

## What you provide

- Notes or transcripts, one block per interview, each starting with an ID line such as `P1 (agency PPC manager)`.
- Your hypotheses, numbered `H1`, `H2`, ...
- Optionally, the decision rule you committed to in advance (for example "supported if 6 of 10").

## The prompt

```text
You are helping me synthesise user interviews. Work ONLY from the notes I paste below.
Do not use outside knowledge about these people or this market.

Rules:
1. Every claim you make must cite the interview ID(s) it comes from, like [P2, P5].
2. Quotes must be copied verbatim from the notes. If there is no direct quote, write "[no direct quote]".
   Never paraphrase inside quotation marks.
3. Keep OBSERVATIONS (what the person said or did) separate from INTERPRETATIONS (what you think it means).
   Label each one.
4. For each hypothesis, report: supporting interviews, contradicting interviews, and interviews that did not
   cover it. Give counts as "N of M interviews", where M is the number of interviews provided.
5. List contradictions between interviews explicitly. Do not average them away.
6. If my pre-committed decision rule is given, apply it literally and say whether it is met. Do not soften it.
7. If something is not in the notes, say "not covered". Do not guess.
8. Finish with: (a) the three most decision-relevant findings, (b) what I could not learn from these notes,
   (c) follow-up questions for the next round.

Output format:
- A table: Hypothesis | Supporting | Contradicting | Not covered | Rule met?
- Then observations and interpretations, grouped by theme, each with citations.

HYPOTHESES:
{paste hypotheses}

DECISION RULES (optional):
{paste rules}

NOTES:
{paste notes}
```

## Check the output

- Pick three quotes at random and find each in your notes. If one is not there verbatim, discard the whole output.
- Add up the counts yourself for one hypothesis.
- Look for a hypothesis where every interview "supports" it. That is rarely true; check whether contradictions were dropped.

## Known failure modes

- **Fabricated or "tidied" quotes.** The most dangerous failure; the check above exists for it.
- **Over-agreement.** Models tend to find support for hypotheses you state. Add hypotheses you expect to be false.
- **Counting errors** on longer note sets. Verify counts.
- **Treating interview volume as prevalence.** Ten interviews describe ten people, not a market.
