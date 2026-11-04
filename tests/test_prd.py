from pmkit.prd import FAIL, PASS, WARN, check_prd, parse_sections, summarize

GOOD = """
# Checkout redesign

## Problem
Shoppers abandon checkout at the payment step. Support tickets about failed payments rose last quarter and
interviews suggest the form is confusing on mobile screens.

## Target users
Mobile shoppers on small screens, and support agents who handle payment failures every day.

## Goals
- Reduce payment-step abandonment from 38% to 30% within one quarter.
- Cut payment-related support tickets by 20%.

## Non-goals
- Adding new payment providers.
- Redesigning the cart page.

## Success metrics
Primary: payment-step completion rate, baseline 62%, target 70%.
Guardrail: refund rate must not increase; average order value must not fall.

## Requirements
1. Single-page payment form with inline validation.
2. Saved payment methods for returning shoppers.

## Risks
- Fraud rises if validation is loosened. Mitigation: keep server-side checks and monitor chargebacks.

## Open questions
- Do we need legal review for saved cards?

## Rollout
Phase 1: 5% of mobile traffic for two weeks. Phase 2: everyone if guardrails hold.
"""


def by_check(findings, check):
    return [f for f in findings if f.check == check]


def test_a_complete_prd_has_no_failures_or_warnings():
    findings = check_prd(GOOD)
    assert summarize(findings)[FAIL] == 0 and summarize(findings)[WARN] == 0, [f for f in findings if f.status != PASS]


def test_missing_sections_fail():
    findings = check_prd("# Idea\n\n## Problem\nPeople want a thing and it would be nice if they had it somehow today.\n")
    missing = {f.message for f in findings if f.status == FAIL}
    assert "No non-goals section found." in missing and "No success metrics section found." in missing


def test_metrics_without_numbers_fail():
    doc = GOOD.replace("Primary: payment-step completion rate, baseline 62%, target 70%.\nGuardrail: refund rate must not increase; average order value must not fall.",
                       "We will know it worked when checkout feels smooth and shoppers are happy with the experience overall.")
    findings = check_prd(doc)
    assert any(f.check == "metrics" and f.status == FAIL and "no numbers" in f.message for f in findings)


def test_missing_guardrail_warns():
    doc = GOOD.replace("Guardrail: refund rate must not increase; average order value must not fall.", "Secondary: tickets down.")
    assert any(f.check == "metrics" and f.status == WARN and "guardrail" in f.message for f in check_prd(doc))


def test_empty_non_goals_fail_even_though_the_heading_exists():
    doc = GOOD.replace("- Adding new payment providers.\n- Redesigning the cart page.\n", "")
    findings = check_prd(doc)
    assert any(f.status == FAIL and "non-goals section is empty" in f.message for f in findings)


def test_vague_words_without_measure_warn_but_numbers_rescue_them():
    doc = GOOD.replace("- Cut payment-related support tickets by 20%.", "- Make the checkout better and more seamless.")
    vague = by_check(check_prd(doc), "vague")
    assert vague and "better" in vague[0].message
    assert not by_check(check_prd(GOOD), "vague")      # "Reduce ... from 38% to 30%" has numbers


def test_placeholders_warn_with_line_numbers_but_html_comments_are_ignored():
    doc = GOOD + "\n## Notes\nTBD: pricing.\n<!-- TODO: remove this guidance comment -->\n"
    ph = by_check(check_prd(doc), "placeholder")
    assert len(ph) == 1 and "TBD" in ph[0].message and ph[0].line is not None


def test_risks_without_mitigations_warn():
    doc = GOOD.replace(" Mitigation: keep server-side checks and monitor chargebacks.", "")
    assert any(f.check == "risks" and f.status == WARN for f in check_prd(doc))


def test_metrics_in_a_linked_document_is_a_warning_not_a_failure():
    doc = GOOD.replace("## Success metrics", "## Measurement").replace(
        "Primary: payment-step completion rate, baseline 62%, target 70%.", "See [the metrics plan](metrics.md).")
    findings = check_prd(doc)
    assert any(f.status == WARN and "links to a metrics document" in f.message for f in findings)
    assert not any(f.status == FAIL and f.check == "section" and "success metrics" in f.message for f in findings)


def test_combined_heading_counts_for_both_goals_and_non_goals():
    doc = GOOD.replace("## Goals\n", "## Goals and non-goals\n**Goals**\n").replace("## Non-goals\n", "**Non-goals**\n")
    assert summarize(check_prd(doc))[FAIL] == 0


def test_bold_label_lines_act_as_subheadings():
    titles = [s.title for s in parse_sections("## Scope\n**Goals (MVP)**\n- one\n**Non-goals (MVP)**\n- two\n")]
    assert "Goals (MVP)" in titles and "Non-goals (MVP)" in titles


def test_headings_inside_code_fences_are_ignored():
    sections = parse_sections("## Real\n```\n## Not a heading\n```\n")
    assert [s.title for s in sections] == ["Real"]


def test_thin_document_warns():
    assert any(f.check == "length" for f in check_prd("# PRD\n\nBuild it.\n"))


def test_a_bare_success_heading_is_treated_as_the_metrics_section():
    doc = "# X\n\n## Success\nWe will know it worked when users are happy with the new experience overall.\n"
    findings = check_prd(doc)
    assert any(f.check == "metrics" and f.status == FAIL and "no numbers" in f.message for f in findings)
