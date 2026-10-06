"""Monthly value model for one agent use case: cost lines, capacity vs cash, sensitivity,
combined pessimistic case and funding verdict.

  python roi_model.py                 # demo inputs, runs the self-check
  python roi_model.py inputs.json     # your inputs; keys you leave out keep the defaults

inputs.json may also hold:
  "currency": "EUR"
  "measured": ["volume", "rate", ...]      inputs backed by own data (system history counts)
  "ranges": {"contained": [0.4, 0.85], ...} realistic low/high per input (default x0.5..x2)
Without a realistic "contained" range the script gives no funding verdict.
"""
import json
import sys

DEFAULTS = {
    "volume": 20_000,        # items per month in scope
    "human_min": 5.0,        # person-minutes of effort per item today (not open-to-close time)
    "rate": 40.0,            # loaded cost per person-hour
    "contained": 0.70,       # share the agent closes with no person (0 for an assist-only agent)
    "escalated_min": 5.0,    # person-minutes per item the agent does not close
    "qa_share": 0.10,        # share of agent-closed items a person checks (1.0 = approve every item)
    "qa_min": 1.0,           # minutes per check or approval
    "run_cost": 0.04,        # agent cost per item: model, tools, infra
    "err_rate": 0.02,        # wrong outcomes per agent-closed item
    "err_cost": 25.0,        # cost per wrong outcome: refund, rework, goodwill, exposure
    "platform": 8_000.0,     # monthly share of platform, monitoring, on-call
    "pilot_cost": 60_000.0,  # one-off spend before the scale decision: money at risk if killed
    "build": 120_000.0,      # total one-off cost to full deployment, pilot included
    "cash_share": 0.0,       # share of freed hours that becomes cash (hiring, overtime, temps cut)
    "fte_hours": 160.0,      # paid hours per person per month
}
BASELINE = ("volume", "human_min", "rate")      # facts: measure them before the pilot
PILOT = ("contained", "escalated_min", "err_rate", "err_cost", "qa_share", "qa_min")  # only a pilot measures these
ESTIMATES = ("run_cost", "platform")            # quotes and engineering estimates
SHARES = {"contained", "qa_share", "err_rate", "cash_share"}


def monthly(p):
    hour = p["rate"] / 60
    closed = p["volume"] * p["contained"]
    people = {"escalated work": (p["volume"] - closed) * p["escalated_min"] * hour,
              "checks and approvals": closed * p["qa_share"] * p["qa_min"] * hour}
    cash = {"agent run cost": p["volume"] * p["run_cost"],
            "wrong outcomes": closed * p["err_rate"] * p["err_cost"],
            "platform share": p["platform"]}
    baseline = p["volume"] * p["human_min"] * hour
    labour = baseline - sum(people.values())          # freed hours priced at the loaded rate
    net = labour - sum(cash.values())                 # capacity-valued
    net_cash = labour * p["cash_share"] - sum(cash.values())
    return {"baseline": baseline, "people": people, "cash": cash, "labour": labour,
            "hours_freed": labour / p["rate"], "net": net, "net_cash": net_cash,
            "payback": p["build"] / net if net > 0 else float("inf")}


def vary(p, key, value):
    """Change one input. Escalated handling time scales with the baseline handling time."""
    q = {**p, key: value}
    if key == "human_min" and p["human_min"]:
        q["escalated_min"] = p["escalated_min"] * value / p["human_min"]
    return q


def span(p, ranges, key):
    lo, hi = ranges.get(key, (p[key] * 0.5, p[key] * 2))
    return (max(0.0, lo), min(1.0, hi)) if key in SHARES else (lo, hi)


def breakeven_containment(p):
    """Net is linear in containment, so two points give the share where net = 0."""
    n0, n1 = monthly({**p, "contained": 0.0})["net"], monthly({**p, "contained": 1.0})["net"]
    return None if n1 == n0 else -n0 / (n1 - n0)


def sensitivity(p, ranges, keys):
    rows = []
    for key in keys:
        lo, hi = span(p, ranges, key)
        n_lo, n_hi = monthly(vary(p, key, lo))["net"], monthly(vary(p, key, hi))["net"]
        rows.append((abs(n_hi - n_lo), key, lo, hi, n_lo, n_hi))
    return sorted(rows, reverse=True)


def pessimistic(p, ranges):
    """Pilot uncertainties and estimates at their bad ends; baseline facts held."""
    q = dict(p)
    for key in PILOT + ESTIMATES:
        lo, hi = span(p, ranges, key)
        q[key] = lo if monthly(vary(p, key, lo))["net"] < monthly(vary(p, key, hi))["net"] else hi
    return q


def verdicts(p, ranges, measured, r, cur):
    out = []
    assumed = [k for k in BASELINE if k not in measured]
    if assumed:
        out.append(f"UNVALIDATED, pilot required: baseline facts assumed ({', '.join(assumed)}). "
                   "Measure them first; system history over a stated period counts.")
    open_pilot = [k for k in PILOT if k not in measured]
    if open_pilot:
        out.append(f"Pilot must measure: {', '.join(open_pilot)}.")
    be = breakeven_containment(p)
    if be is None or not 0 <= be <= 1:
        out.append("NOT FUNDABLE: net is negative at every containment level." if r["net"] <= 0 else
                   "Net is positive at any containment; set kill lines on error rate and guardrails.")
        return out
    floor = min(be + 0.10, 1.0)
    if "contained" not in ranges:
        out.append(f"No funding verdict: give a realistic containment range (breakeven {be:.0%}, needs a low end of {floor:.0%} or more).")
        return out
    low, high = span(p, ranges, "contained")
    if high < floor:
        out.append(f"NOT FUNDABLE: even the realistic high end {high:.0%} is under breakeven + 10 points ({floor:.0%}); "
                   "a pilot could not pass its own kill line.")
    elif low >= floor:
        rule = (f"kill below {low:.0%} containment (the realistic low end); exit threshold = net at that "
                f"level, {cur} {monthly({**p, 'contained': low})['net']:,.0f}/month")
        out.append(f"PILOT ONLY until the baseline is measured; provisional rule: {rule}." if assumed else
                   f"FUNDABLE: fund the pilot; scale on meeting exit criteria. {rule[0].upper() + rule[1:]}.")
    else:
        out.append(f"PILOT ONLY: realistic low end {low:.0%} is under breakeven + 10 points ({floor:.0%}). "
                   f"Fund the pilot ({cur} {p['pilot_cost']:,.0f}) and kill below {floor:.0%}; "
                   "the full build waits for measured containment. Do not move the range to pass this test.")
    return out


def report(p, ranges, measured, cur):
    r = monthly(p)
    m = lambda v: f"{cur} {v:>10,.0f}"
    fmt = lambda v: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.3g}"
    pay = lambda x: "no payback" if x == float("inf") else f"payback {x:.1f} months"
    parts = lambda d: "; ".join(f"{k} {v:,.0f}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))
    print(f"baseline cost             {m(r['baseline'])} /month")
    print(f"people time still needed  {m(sum(r['people'].values()))}  ({parts(r['people'])})")
    note = "capacity, not cash" if r["hours_freed"] >= 0 else "negative: the agent adds human work"
    print(f"value of freed time       {m(r['labour'])}  = {r['hours_freed']:,.0f} h/month, ~{r['hours_freed'] / p['fte_hours']:.1f} FTE ({note})")
    print(f"cash costs                {m(sum(r['cash'].values()))}  ({parts(r['cash'])})")
    print(f"net, capacity-valued      {m(r['net'])} /month; {pay(r['payback'])} on {cur} {p['build']:,.0f} one-off")
    print(f"net cash                  {m(r['net_cash'])} /month with {p['cash_share']:.0%} of freed hours turned into savings (cash_share)")
    print(f"pilot spend at risk       {m(p['pilot_cost'])}")
    be = breakeven_containment(p)
    if be is not None and 0 <= be <= 1:
        print(f"breakeven containment     {be:.0%}; floor = breakeven + 10 points = {min(be + 0.10, 1.0):.0%}")
    q = pessimistic(p, ranges)
    rq = monthly(q)
    bad = ", ".join(f"{k}={fmt(q[k])}" for k in PILOT + ESTIMATES)
    print(f"combined pessimistic      {m(rq['net'])} /month; {pay(rq['payback'])} ({bad})")
    for title, keys in (("baseline facts: measure before the pilot", BASELINE),
                        ("pilot uncertainties: the pilot measures these", PILOT),
                        ("estimates: firm up with quotes", ESTIMATES)):
        print(f"\nsensitivity, {title} (net/month at low .. high)")
        for swing, key, lo, hi, n_lo, n_hi in sensitivity(p, ranges, keys):
            label = key + ("*" if key == "human_min" else "")
            print(f"  {label:14} {fmt(lo):>8} .. {fmt(hi):<8} net {n_lo:>10,.0f} .. {n_hi:<10,.0f} swing {swing:,.0f}")
    print("  * escalated_min scales with human_min")
    print("\nverdict")
    for line in verdicts(p, ranges, measured, r, cur):
        print("  - " + line)
    return r


if __name__ == "__main__":
    user = json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 else {}
    cur = user.pop("currency", "USD")
    measured = set(user.pop("measured", []))
    ranges = {k: tuple(v) for k, v in user.pop("ranges", {}).items()}
    unknown = (set(user) | set(ranges) | measured) - set(DEFAULTS)
    if unknown:
        sys.exit(f"unknown inputs: {sorted(unknown)}")
    result = report({**DEFAULTS, **user}, ranges, measured, cur)
    if not user:  # self-check on the demo inputs
        assert round(result["net"]) == 29_933 and round(result["payback"], 1) == 4.0
        assert round(monthly({**DEFAULTS, "contained": 0.40})["net"]) == 13_333
        assert abs(monthly({**DEFAULTS, "contained": breakeven_containment(DEFAULTS)})["net"]) < 1e-6
        half = vary(DEFAULTS, "human_min", 2.5)
        assert half["escalated_min"] == 2.5 and round(monthly(half)["net"]) == 6_600
        assert monthly(pessimistic(DEFAULTS, {}))["net"] < result["net"]
        assert round(result["net_cash"]) == -15_800  # nothing converted: only the cash costs remain
        v = lambda rng, meas=(): " ".join(verdicts(DEFAULTS, rng, set(meas), result, "USD"))  # breakeven 16%, floor 26%
        assert "No funding verdict" in v({})
        assert "FUNDABLE: fund the pilot" in v({"contained": (0.4, 0.9)}, BASELINE)
        assert "PILOT ONLY: realistic low end" in v({"contained": (0.2, 0.8)}, BASELINE)
        assert "NOT FUNDABLE: even" in v({"contained": (0.1, 0.2)}, BASELINE)
        assert v({"contained": (0.4, 0.9)}).startswith("UNVALIDATED") and "PILOT ONLY until" in v({"contained": (0.4, 0.9)})
        print("\nself-check ok")
