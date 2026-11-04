"""A deterministic checker for product requirements documents (Markdown).

It looks for the omissions and habits a careful reviewer flags in the first five minutes:
missing sections, empty non-goals, success metrics with no numbers, vague words with no
measure, unfinished placeholders. It does NOT judge whether the product idea is good,
whether the metrics are the right ones, or whether the writing is clear. A document can pass
every check and still be a bad PRD; the checker only removes the cheap-to-catch problems.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PASS, WARN, FAIL = "pass", "warn", "fail"

# Heading text -> category. A heading can satisfy several (e.g. "Risks and open questions").
CATEGORY_PATTERNS: dict[str, str] = {
    "problem": r"\b(problem|background|context|opportunity|motivation|why now)\b",
    "users": r"\b(users?|customers?|personas?|audience|target|who is this for|stakeholders?)\b",
    "goals": r"(?<!non-)(?<!non )\b(goals?|objectives?)\b",
    "non_goals": r"\bnon[- ]?goals?\b|\bout of scope\b|\bnot doing\b|\bwon'?t do\b",
    "metrics": r"\b(success(?: criteria| metrics?)?|metrics?|kpis?|okrs?|measures? of success)\b",
    "requirements": r"\b(requirements?|scope|user stories|features?|solution|proposal)\b",
    "risks": r"\b(risks?|mitigations?)\b",
    "open_questions": r"\b(open questions?|unknowns?|assumptions?)\b",
    "rollout": r"\b(rollout|launch|release|timeline|milestones?|phas(?:e|es|ing))\b",
}
REQUIRED = ["problem", "users", "goals", "non_goals", "metrics", "requirements", "risks"]
RECOMMENDED = ["open_questions", "rollout"]
LABELS = {
    "problem": "problem", "users": "users", "goals": "goals", "non_goals": "non-goals",
    "metrics": "success metrics", "requirements": "requirements", "risks": "risks",
    "open_questions": "open questions", "rollout": "rollout",
}

VAGUE = re.compile(
    r"\b(better|improv(?:e|es|ed|ing)|seamless(?:ly)?|intuitive|user-friendly|robust|easy|easier|simple|"
    r"simplif\w+|fast(?:er)?|enhanc\w+|optimi[sz]\w*|streamlin\w+|world-class|best-in-class|delight\w*|leverag\w+)\b",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(r"\b(TBD|TODO|FIXME|XXX)\b|lorem ipsum|\[(?:insert|add|describe|fill)[^\]]*\]", re.IGNORECASE)
GUARDRAIL = re.compile(r"guardrail|counter[- ]?metric|must not (?:fall|drop|regress|increase)|do no harm|should not regress", re.IGNORECASE)
BOLD_LINE = re.compile(r"^\s*\*\*(.+?)\*\*:?\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass
class Finding:
    status: str
    check: str
    message: str
    line: int | None = None


@dataclass
class Section:
    title: str
    level: int            # 1..6 for '#' headings; 7 for a bold label line
    line: int             # 1-based
    lines: list[tuple[int, str]] = field(default_factory=list)  # content incl. sub-sections

    @property
    def text(self) -> str:
        return "\n".join(t for _, t in self.lines)

    @property
    def words(self) -> int:
        return len(re.findall(r"[A-Za-z0-9%$]+", self.text))


_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")
_BRACKETED = re.compile(r"\[[^\]]*\]")


def _has_number(text: str) -> bool:
    """True if the text states a number. Digits in [unfilled placeholders], link URLs and list numbering do not count."""
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)  # "1. " list numbering is not a quantity
    return bool(re.search(r"\d", _BRACKETED.sub(" ", _LINK.sub(" ", text))))


def _blank_html_comments(text: str) -> str:
    """Remove <!-- comments --> but keep line numbers stable."""
    return HTML_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def parse_sections(text: str) -> list[Section]:
    raw = _blank_html_comments(text).splitlines()
    heads: list[tuple[int, int, str]] = []  # (index, level, title)
    in_fence = False
    for i, line in enumerate(raw):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
        else:
            b = BOLD_LINE.match(line)
            if b:
                heads.append((i, 7, b.group(1)))
    sections = []
    for k, (i, level, title) in enumerate(heads):
        end = len(raw)
        for j, lvl, _ in heads[k + 1:]:
            if lvl <= level:
                end = j
                break
        body = [(n + 1, raw[n]) for n in range(i + 1, end)]
        sections.append(Section(re.sub(r"^\d+[.)]?\s*", "", title), level, i + 1, body))
    return sections


def _find(sections: list[Section], category: str) -> list[Section]:
    pattern = re.compile(CATEGORY_PATTERNS[category], re.IGNORECASE)
    return [s for s in sections if pattern.search(s.title)]


def _meaningful_words(section: Section) -> int:
    words = 0
    for _, line in section.lines:
        if HEADING.match(line) or BOLD_LINE.match(line):
            continue
        words += len(re.findall(r"[A-Za-z0-9%$]+", line))
    return words


def check_prd(text: str) -> list[Finding]:
    clean = _blank_html_comments(text)
    sections = parse_sections(text)
    findings: list[Finding] = []
    total_words = len(re.findall(r"[A-Za-z0-9%$]+", clean))

    # 1. Required and recommended sections
    for group, level in ((REQUIRED, FAIL), (RECOMMENDED, WARN)):
        for cat in group:
            found = _find(sections, cat)
            label = LABELS[cat]
            if not found:
                if cat == "metrics" and re.search(r"\[[^\]]*metric[^\]]*\]\([^)]+\)", clean, re.IGNORECASE):
                    findings.append(Finding(WARN, "section", "No success-metrics section; the document links to a metrics document. "
                                            "A PRD should state its own primary metric, even if details live elsewhere."))
                else:
                    findings.append(Finding(level, "section", f"No {label} section found."))
                continue
            first = found[0]
            if max(_meaningful_words(s) for s in found) < 6:
                findings.append(Finding(FAIL if cat in REQUIRED else WARN, "section",
                                        f"The {label} section is empty or nearly empty.", first.line))
            else:
                findings.append(Finding(PASS, "section", f"{label.capitalize()} section present.", first.line))

    # 2. Success metrics: numbers and a guardrail
    for s in _find(sections, "metrics"):
        if _meaningful_words(s) < 6:
            continue
        if not _has_number(s.text):
            findings.append(Finding(FAIL, "metrics", "Success metrics contain no numbers. State a baseline and a target "
                                    "(or say explicitly that the baseline is unknown).", s.line))
        else:
            findings.append(Finding(PASS, "metrics", "Success metrics include numbers.", s.line))
        if not GUARDRAIL.search(s.text):
            findings.append(Finding(WARN, "metrics", "No guardrail metric mentioned: what must not get worse while "
                                    "the primary metric improves?", s.line))
        break

    # 3. Risks should come with mitigations
    risks = _find(sections, "risks")
    if risks and max(_meaningful_words(s) for s in risks) >= 6:
        if re.search(r"mitigat", "\n".join(s.text for s in risks), re.IGNORECASE):
            findings.append(Finding(PASS, "risks", "Risks mention mitigations.", risks[0].line))
        else:
            findings.append(Finding(WARN, "risks", "Risks are listed without mitigations.", risks[0].line))

    # 4. Placeholders left in
    for n, line in enumerate(clean.splitlines(), start=1):
        m = PLACEHOLDER.search(line)
        if m:
            findings.append(Finding(WARN, "placeholder", f'Unfinished placeholder "{m.group(0)}".', n))

    # 5. Vague language with no measure, in goals, metrics and requirements
    vague: list[Finding] = []
    for cat in ("goals", "metrics", "requirements"):
        for s in _find(sections, cat):
            for n, line in s.lines:
                if HEADING.match(line) or BOLD_LINE.match(line):
                    continue
                m = VAGUE.search(line)
                if m and not _has_number(line):
                    snippet = line.strip().lstrip("-*0123456789. ").strip()
                    vague.append(Finding(WARN, "vague", f'"{m.group(0)}" with no measure: "{snippet[:80]}"', n))
    seen, unique = set(), []
    for f in vague:
        if f.line not in seen:
            seen.add(f.line)
            unique.append(f)
    findings.extend(unique[:6])
    if len(unique) > 6:
        findings.append(Finding(WARN, "vague", f"...and {len(unique) - 6} more vague lines in goals, metrics and requirements."))

    # 6. Thin document
    if total_words < 150:
        findings.append(Finding(WARN, "length", f"Only {total_words} words. Too thin to align a team."))

    order = {FAIL: 0, WARN: 1, PASS: 2}
    return sorted(findings, key=lambda f: (order[f.status], f.line or 0))


def summarize(findings: list[Finding]) -> dict[str, int]:
    return {s: sum(f.status == s for f in findings) for s in (FAIL, WARN, PASS)}
