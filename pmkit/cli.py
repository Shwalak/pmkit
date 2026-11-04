"""Command-line interface for pmkit."""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys

from . import __version__
from .abtest import (
    Arm,
    Readout,
    days_needed,
    minimum_detectable_effect,
    readout,
    sample_size_per_arm,
)

ASSUMPTIONS = (
    "Valid if: the sample size was fixed in advance, you looked at the data once, this is the one primary\n"
    "metric, and each user appears once. Peeking early, testing many metrics or repeat users make the\n"
    "p-value look better than it is."
)


def parse_arm(text: str) -> Arm:
    """Parse 'conversions/visitors', e.g. 200/1000."""
    try:
        conv, vis = text.replace(",", "").split("/")
        return Arm(int(conv), int(vis))
    except ValueError as exc:
        if "must be" in str(exc) or "positive" in str(exc):
            raise
        raise ValueError(f"expected conversions/visitors such as 200/1000, got {text!r}") from None


def _pp(x: float) -> str:
    return f"{x * 100:+.2f} pp"


def format_readout(r: Readout) -> str:
    lines = [
        "A/B test readout (two arms, yes/no metric)",
        "",
        f"  {'':10}{'visitors':>10}{'conversions':>13}{'rate':>9}",
        f"  {'control':10}{r.control.visitors:>10,}{r.control.conversions:>13,}{r.control.rate * 100:>8.2f}%",
        f"  {'treatment':10}{r.treatment.visitors:>10,}{r.treatment.conversions:>13,}{r.treatment.rate * 100:>8.2f}%",
        "",
        f"Difference:   {_pp(r.difference)}"
        + ("" if r.relative_lift is None else f"   (relative lift {r.relative_lift * 100:+.1f}%)"),
        f"{(1 - r.alpha) * 100:g}% interval: {_pp(r.ci_low)} to {_pp(r.ci_high)}",
        f"p-value:      {r.p_value:.4f}   (pooled two-proportion z-test, two-sided)",
        f"Split check:  {'ALERT' if r.srm_p < 0.001 else 'ok'}   (sample ratio mismatch p = {r.srm_p:.3g})",
        "",
        f"Reading: {r.summary}",
    ]
    for w in r.warnings:
        lines += ["", f"Warning: {w}"]
    lines += ["", ASSUMPTIONS]
    return "\n".join(lines)


def _clean(obj):
    if isinstance(obj, float) and math.isinf(obj):
        return None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def cmd_readout(args: argparse.Namespace) -> int:
    r = readout(parse_arm(args.control), parse_arm(args.treatment), alpha=args.alpha, treatment_share=args.treatment_share)
    if args.json:
        data = _clean(dataclasses.asdict(r))
        data["control"]["rate"], data["treatment"]["rate"] = r.control.rate, r.treatment.rate
        print(json.dumps(data, indent=2))
    else:
        print(format_readout(r))
    return 0


def cmd_size(args: argparse.Namespace) -> int:
    if (args.mde_abs is None) == (args.mde_rel is None):
        raise ValueError("give exactly one of --mde-abs (percentage points, as a fraction) or --mde-rel (relative change)")
    mde_abs = args.mde_abs if args.mde_abs is not None else args.baseline * args.mde_rel
    n = sample_size_per_arm(args.baseline, mde_abs, args.alpha, args.power)
    out = {
        "baseline": args.baseline,
        "absolute_change_to_detect": mde_abs,
        "alpha": args.alpha,
        "power": args.power,
        "visitors_per_arm": n,
        "visitors_total": 2 * n,
    }
    if args.daily_visitors:
        out["days_needed"] = days_needed(n, args.daily_visitors)
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    lines = [
        f"To detect a change from {args.baseline * 100:.2f}% to {(args.baseline + mde_abs) * 100:.2f}% "
        f"({_pp(mde_abs)}), alpha {args.alpha}, power {args.power * 100:g}%:",
        "",
        f"  Visitors per arm: {n:,}",
        f"  Visitors total:   {2 * n:,}",
    ]
    if args.daily_visitors:
        lines.append(f"  Duration:         {out['days_needed']} days at {args.daily_visitors:,.0f} visitors/day (both arms combined)")
    lines += ["", "Run for whole weeks if behaviour differs by day of week, and decide the sample size BEFORE you start."]
    print("\n".join(lines))
    return 0


def cmd_mde(args: argparse.Namespace) -> int:
    mde = minimum_detectable_effect(args.baseline, args.n_per_arm, args.alpha, args.power)
    if args.json:
        print(json.dumps({"baseline": args.baseline, "n_per_arm": args.n_per_arm,
                          "minimum_detectable_effect": None if math.isinf(mde) else mde}, indent=2))
        return 0
    if math.isinf(mde):
        print(f"With {args.n_per_arm:,} visitors per arm, no change from a {args.baseline * 100:.2f}% baseline could be detected reliably.")
    else:
        print(
            f"With {args.n_per_arm:,} visitors per arm and a {args.baseline * 100:.2f}% baseline, the test can reliably "
            f"({args.power * 100:g}% power) detect an increase of about {mde * 100:.2f} pp or more "
            f"(to {(args.baseline + mde) * 100:.2f}%). Smaller real effects will often be missed."
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pmkit", description="A small, tested toolkit for product managers.")
    parser.add_argument("--version", action="version", version=f"pmkit {__version__}")
    top = parser.add_subparsers(dest="group", required=True)

    ab = top.add_parser("ab", help="A/B test planning and readout (yes/no metrics)").add_subparsers(dest="command", required=True)

    r = ab.add_parser("readout", help="read the result of a finished test")
    r.add_argument("--control", required=True, help="conversions/visitors, e.g. 200/1000")
    r.add_argument("--treatment", required=True, help="conversions/visitors, e.g. 240/1000")
    r.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    r.add_argument("--treatment-share", type=float, default=0.5, help="planned share of traffic in treatment (default 0.5)")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_readout)

    s = ab.add_parser("size", help="how many visitors a test needs")
    s.add_argument("--baseline", type=float, required=True, help="current conversion rate, e.g. 0.10")
    s.add_argument("--mde-abs", type=float, help="smallest absolute change worth detecting, e.g. 0.02 for 2 points")
    s.add_argument("--mde-rel", type=float, help="smallest relative change worth detecting, e.g. 0.10 for +10%%")
    s.add_argument("--alpha", type=float, default=0.05)
    s.add_argument("--power", type=float, default=0.80)
    s.add_argument("--daily-visitors", type=float, help="total daily traffic, to estimate duration")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_size)

    m = ab.add_parser("mde", help="the smallest effect a test of a given size can detect")
    m.add_argument("--baseline", type=float, required=True)
    m.add_argument("--n-per-arm", type=int, required=True)
    m.add_argument("--alpha", type=float, default=0.05)
    m.add_argument("--power", type=float, default=0.80)
    m.add_argument("--json", action="store_true")
    m.set_defaults(func=cmd_mde)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
