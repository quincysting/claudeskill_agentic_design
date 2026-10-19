"""Monthly value model for one agent use case: cost lines, capacity vs cash, sensitivity,
combined pessimistic case and funding verdict.

  python roi_model.py                 # demo inputs, runs the self-check
  python roi_model.py inputs.json     # your inputs; keys you leave out keep the defaults

inputs.json may also hold:
  "currency": "EUR"
  "measured": ["volume", "rate", ...]      inputs backed by own data (system history counts)
  "ranges": {"contained": [0.4, 0.85], ...} realistic low/high per input (default x0.5..x2)
  "range_evidence": {"contained": "shadow run, 400 items, Sep 2026"}  what each range rests on
Without a realistic "contained" range the script gives no funding verdict, and without evidence for
that range (a shadow run, a ticket sample, a comparable deployment) the verdict is not firm.
A verdict built on an assumed baseline is provisional in both directions.
"""
import json
import sys

DEFAULTS = {
    "volume": 20_000,        # items per month in scope
    "human_min": 5.0,        # person-minutes of effort per item today (not open-to-close time)
    "rate": 40.0,            # loaded cost per person-hour
    "human_err_rate": 0.0,   # wrong outcomes per item people produce today; the agent is charged only above it
    "contained": 0.70,       # share the agent closes with no person (0 for an assist-only agent)
    "escalated_min": 5.0,    # person-minutes per item the agent does not close
    "qa_share": 0.10,        # share of agent-closed items a person checks (1.0 = approve every item)
    "qa_min": 1.0,           # minutes per check or approval
    "run_cost": 0.04,        # agent cost per item in scope: model, tools, infra
    "fee_per_closed": 0.0,   # vendor price per item the agent closes (outcome pricing), on top of run_cost
    "err_rate": 0.02,        # wrong outcomes per agent-closed item (the agent's absolute rate)
    "err_cost": 25.0,        # cost per wrong outcome: refund, rework, goodwill, exposure
    "platform": 8_000.0,     # monthly share of platform, monitoring, on-call
    "pilot_cost": 60_000.0,  # one-off spend before the scale decision: money at risk if killed
    "build": 120_000.0,      # total one-off cost to full deployment, pilot included
    "cash_share": 0.0,       # share of freed hours that becomes cash (hiring, overtime, temps cut)
    "fte_hours": 160.0,      # paid hours per person per month
}
BASELINE = ("volume", "human_min", "rate")      # facts: measure them before the pilot
TODAY = BASELINE + ("human_err_rate",)          # shown with the baseline facts; 0 (no offset) is the cautious default
PILOT = ("contained", "escalated_min", "err_rate", "err_cost", "qa_share", "qa_min")  # only a pilot measures these
ESTIMATES = ("run_cost", "fee_per_closed", "platform")  # quotes and engineering estimates
SHARES = {"contained", "qa_share", "err_rate", "human_err_rate", "cash_share"}


POSITIVE = {"volume", "human_min", "rate", "fte_hours"}  # divided by, or meaningless at zero


def validate(p, ranges, evidence=None):
    """Exit with a one-line message on bad input, before any arithmetic (no tracebacks, no impossible values)."""
    def check(key, v, where):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            sys.exit(f"{where}: need a number, got {v!r}")
        if key in POSITIVE and v <= 0:
            sys.exit(f"{where}: {v} must be above 0")
        if v < 0 or (key in SHARES and v > 1):
            sys.exit(f"{where}: {v} is out of range ({'0 to 1' if key in SHARES else '>= 0'})")
    for key in DEFAULTS:
        check(key, p[key], key)
    for key, pair in ranges.items():
        if len(pair) != 2:
            sys.exit(f"ranges.{key}: need [low, high]")
        for v in pair:
            check(key, v, f"ranges.{key}")
        if pair[0] > pair[1]:
            sys.exit(f"ranges.{key}: low {pair[0]} is above high {pair[1]}")
    for key, text in (evidence or {}).items():
        if not isinstance(text, str) or not text.strip():
            sys.exit(f"range_evidence.{key}: need a short description of the evidence, got {text!r}")


def load_inputs(path):
    """The user's inputs from a JSON file, or a one-line error."""
    try:
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
    except FileNotFoundError:
        sys.exit(f"{path}: file not found")
    except json.JSONDecodeError as e:
        sys.exit(f"{path}: not valid JSON ({e.msg}, line {e.lineno})")
    if not isinstance(user, dict):
        sys.exit(f"{path}: inputs must be a JSON object, not {type(user).__name__}")
    if (not isinstance(user.get("ranges", {}), dict) or not isinstance(user.get("measured", []), list)
            or not isinstance(user.get("range_evidence", {}), dict)):
        sys.exit(f"{path}: \"ranges\" and \"range_evidence\" must be objects and \"measured\" a list")
    return user


def monthly(p):
    hour = p["rate"] / 60
    closed = p["volume"] * p["contained"]
    people = {"escalated work": (p["volume"] - closed) * p["escalated_min"] * hour,
              "checks and approvals": closed * p["qa_share"] * p["qa_min"] * hour}
    cash = {"agent run cost": p["volume"] * p["run_cost"] + closed * p["fee_per_closed"],
            "wrong outcomes above today's rate": closed * (p["err_rate"] - p["human_err_rate"]) * p["err_cost"],
            "platform share": p["platform"]}
    baseline = p["volume"] * p["human_min"] * hour
    labour = baseline - sum(people.values())          # freed hours priced at the loaded rate
    net = labour - sum(cash.values())                 # capacity-valued
    net_cash = labour * p["cash_share"] - sum(cash.values())
    return {"baseline": baseline, "people": people, "cash": cash, "labour": labour,
            "hours_freed": labour / p["rate"], "net": net, "net_cash": net_cash,
            "payback": p["build"] / net if net > 0 else float("inf"),
            "payback_cash": p["build"] / net_cash if net_cash > 0 else float("inf")}


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


def cash_view(p, r, cur):
    """The cash basis, stated next to any positive verdict that rests on capacity value alone."""
    if r["net"] > 0 and r["net_cash"] < 0:
        return [f"CASH VIEW: net cash is {cur} {r['net_cash']:,.0f}/month at cash_share {p['cash_share']:.0%}. "
                "Any positive verdict here rests on capacity value: the case loses cash every month until freed "
                "hours have a committed destination (hiring stopped, overtime or contractors cut)."]
    return []


def verdicts(p, ranges, measured, r, cur, evidence=()):
    """Verdict lines. An assumed baseline heads them UNVALIDATED, with "pilot required" only on a positive verdict."""
    out = funding(p, ranges, measured, r, cur, evidence)
    assumed = [k for k in BASELINE if k not in measured]
    if assumed:
        positive = any(line.startswith(("PILOT ONLY", "Net is positive")) for line in out)
        out.insert(0, f"UNVALIDATED{': pilot required' if positive else ''}. Baseline facts assumed "
                      f"({', '.join(assumed)}): measure them first; system history over a stated period counts.")
    return out


def funding(p, ranges, measured, r, cur, evidence):
    out = []
    assumed = [k for k in BASELINE if k not in measured]
    open_pilot = [k for k in PILOT if k not in measured]
    if open_pilot:
        out.append(f"Pilot must measure: {', '.join(open_pilot)}.")
    be = breakeven_containment(p)
    if be is None or not 0 <= be <= 1:
        if r["net"] > 0:
            out.append("Net is positive at any containment; set kill lines on error rate and guardrails.")
        elif assumed:
            out.append("NOT FUNDABLE on assumed inputs: net is negative at every containment level on an assumed "
                       "baseline. Not a firm verdict: measure the baseline before any pilot spend, then re-run.")
        else:
            out.append("NOT FUNDABLE: net is negative at every containment level.")
        return out + cash_view(p, r, cur)
    floor = min(be + 0.10, 1.0)
    if "contained" not in ranges:
        out.append(f"No funding verdict: give a realistic containment range (breakeven {be:.0%}, needs a low end of {floor:.0%} or more).")
        return out + cash_view(p, r, cur)
    low, high = span(p, ranges, "contained")
    if high < floor:
        name, why = "NOT FUNDABLE", (f"even the realistic high end {high:.0%} is under breakeven + 10 points "
                                     f"({floor:.0%}); a pilot could not pass its own kill line")
    elif low >= floor:
        name, why = "FUNDABLE", (f"kill below {low:.0%} containment (the realistic low end); exit threshold = net at "
                                 f"that level, {cur} {monthly({**p, 'contained': low})['net']:,.0f}/month")
    else:
        name, why = "PILOT ONLY", (f"realistic low end {low:.0%} is under breakeven + 10 points ({floor:.0%}). "
                                   f"Fund the pilot ({cur} {p['pilot_cost']:,.0f}) and kill below {floor:.0%}; "
                                   "the full build waits for measured containment. Do not move the range to pass this test")
    if "contained" not in measured and "contained" not in evidence:
        out.append("No firm funding verdict: the containment range has no evidence behind it (give a shadow run, "
                   "ticket sample or comparable deployment in range_evidence). First step: a shadow sample of a few "
                   f"hundred real items; re-run with the range it gives. On the current range the model would say {name}.")
    elif name == "NOT FUNDABLE" and assumed:
        out.append(f"NOT FUNDABLE on assumed inputs ({', '.join(assumed)}): not a firm verdict. Measure the baseline "
                   f"before any pilot spend, then re-run. On these inputs {why}.")
    elif name == "FUNDABLE" and assumed:
        out.append(f"PILOT ONLY until the baseline is measured; provisional rule: {why}.")
    elif name == "FUNDABLE":
        out.append(f"FUNDABLE: fund the pilot; scale on meeting exit criteria. {why[0].upper() + why[1:]}.")
    else:
        out.append(f"{name}: {why}.")
    return out + (cash_view(p, r, cur) if name != "NOT FUNDABLE" else [])


def report(p, ranges, measured, cur, evidence=()):
    r = monthly(p)
    m = lambda v: f"{cur} {v:>10,.0f}"
    fmt = lambda v: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.3g}"
    pay = lambda x, what="payback": f"no {what}" if x == float("inf") else f"{what} {x:.1f} months"
    parts = lambda d: "; ".join(f"{k} {v:,.0f}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))
    print(f"baseline cost             {m(r['baseline'])} /month")
    print(f"people time still needed  {m(sum(r['people'].values()))}  ({parts(r['people'])})")
    note = "capacity, not cash" if r["hours_freed"] >= 0 else "negative: the agent adds human work"
    print(f"value of freed time       {m(r['labour'])}  = {r['hours_freed']:,.0f} h/month, ~{r['hours_freed'] / p['fte_hours']:.1f} FTE ({note})")
    print(f"cash costs                {m(sum(r['cash'].values()))}  ({parts(r['cash'])})")
    print(f"net, capacity-valued      {m(r['net'])} /month; {pay(r['payback'])} on {cur} {p['build']:,.0f} one-off")
    print(f"net cash                  {m(r['net_cash'])} /month; {pay(r['payback_cash'], 'cash payback')}; "
          f"{p['cash_share']:.0%} of freed hours turned into savings (cash_share)")
    print(f"pilot spend at risk       {m(p['pilot_cost'])}")
    be = breakeven_containment(p)
    if be is not None and 0 <= be <= 1:
        print(f"breakeven containment     {be:.0%}; floor = breakeven + 10 points = {min(be + 0.10, 1.0):.0%}")
    for key, text in evidence.items():
        print(f"range evidence            {key}: {text}")
    q = pessimistic(p, ranges)
    rq = monthly(q)
    bad = ", ".join(f"{k}={fmt(q[k])}" for k in PILOT + ESTIMATES)
    print(f"combined pessimistic      {m(rq['net'])} /month; {pay(rq['payback'])} ({bad})")
    for title, keys in (("baseline facts: measure before the pilot", TODAY),
                        ("pilot uncertainties: the pilot measures these", PILOT),
                        ("estimates: firm up with quotes", ESTIMATES)):
        print(f"\nsensitivity, {title} (net/month at low .. high)")
        for swing, key, lo, hi, n_lo, n_hi in sensitivity(p, ranges, keys):
            label = key + ("*" if key == "human_min" else "")
            print(f"  {label:14} {fmt(lo):>8} .. {fmt(hi):<8} net {n_lo:>10,.0f} .. {n_hi:<10,.0f} swing {swing:,.0f}")
    print("  * escalated_min scales with human_min")
    print("\nverdict")
    for line in verdicts(p, ranges, measured, r, cur, evidence):
        print("  - " + line)
    return r


if __name__ == "__main__":
    user = load_inputs(sys.argv[1]) if len(sys.argv) > 1 else {}
    cur = str(user.pop("currency", "USD"))
    measured = set(user.pop("measured", []))
    ranges = {k: tuple(v) if isinstance(v, (list, tuple)) else (v,) for k, v in user.pop("ranges", {}).items()}
    evidence = user.pop("range_evidence", {})
    unknown = (set(user) | set(ranges) | measured | set(evidence)) - set(DEFAULTS)
    if unknown:
        sys.exit(f"unknown inputs: {sorted(unknown)}")
    validate({**DEFAULTS, **user}, ranges, evidence)
    result = report({**DEFAULTS, **user}, ranges, measured, cur, evidence)
    if not user:  # self-check on the demo inputs
        assert round(result["net"]) == 29_933 and round(result["payback"], 1) == 4.0
        assert round(monthly({**DEFAULTS, "contained": 0.40})["net"]) == 13_333
        assert abs(monthly({**DEFAULTS, "contained": breakeven_containment(DEFAULTS)})["net"]) < 1e-6
        half = vary(DEFAULTS, "human_min", 2.5)
        assert half["escalated_min"] == 2.5 and round(monthly(half)["net"]) == 6_600
        assert monthly(pessimistic(DEFAULTS, {}))["net"] < result["net"]
        assert round(result["net_cash"]) == -15_800 and result["payback_cash"] == float("inf")  # nothing converted
        assert round(monthly({**DEFAULTS, "cash_share": 1.0})["payback_cash"], 1) == 4.0  # all hours become cash
        # human error offset: 14,000 closed x 2% x 25 = 7,000 no longer charged to the agent
        assert round(monthly({**DEFAULTS, "human_err_rate": 0.02})["net"]) == 36_933
        # outcome pricing: 14,000 closed x 0.50 = 7,000 more cost; breakeven still exact
        fee = {**DEFAULTS, "fee_per_closed": 0.5}
        assert round(monthly(fee)["net"]) == 22_933
        assert abs(monthly({**fee, "contained": breakeven_containment(fee)})["net"]) < 1e-6
        ev = ("contained",)  # breakeven 16%, floor 26%
        v = lambda rng, meas=(), e=ev: " ".join(verdicts(DEFAULTS, rng, set(meas), result, "USD", e))
        assert "No funding verdict" in v({})
        assert "FUNDABLE: fund the pilot" in v({"contained": (0.4, 0.9)}, BASELINE)
        assert "CASH VIEW" in v({"contained": (0.4, 0.9)}, BASELINE)  # fundable on capacity, cash negative
        assert "CASH VIEW" not in " ".join(verdicts(DEFAULTS, {"contained": (0.4, 0.9)}, set(BASELINE),
                                                    monthly({**DEFAULTS, "cash_share": 1.0}), "USD", ev))
        assert "PILOT ONLY: realistic low end" in v({"contained": (0.2, 0.8)}, BASELINE)
        assert "NOT FUNDABLE: even" in v({"contained": (0.1, 0.2)}, BASELINE)
        assert "CASH VIEW" not in v({"contained": (0.1, 0.2)}, BASELINE)  # no cash note on a negative verdict
        assert v({"contained": (0.4, 0.9)}).startswith("UNVALIDATED: pilot required") and "PILOT ONLY until" in v({"contained": (0.4, 0.9)})
        no_base = v({"contained": (0.1, 0.2)})  # assumed baseline: a negative verdict is provisional too
        assert "NOT FUNDABLE on assumed inputs" in no_base and "NOT FUNDABLE: even" not in no_base
        assert no_base.startswith("UNVALIDATED.") and "pilot required" not in no_base  # measure first, no pilot
        assert "pilot required" not in v({"contained": (0.4, 0.9)}, (), ())  # no firm verdict: shadow sample first
        no_ev = v({"contained": (0.1, 0.2)}, BASELINE, ())  # range with no evidence: no firm verdict either way
        assert "No firm funding verdict" in no_ev and "shadow sample" in no_ev and "NOT FUNDABLE:" not in no_ev
        assert "No firm funding verdict" in v({"contained": (0.4, 0.9)}, BASELINE, ())
        assert "FUNDABLE: fund" in v({"contained": (0.4, 0.9)}, BASELINE + ("contained",), ())  # measured counts
        for bad, rng, ev_bad in (({"contained": 1.5}, {}, {}), ({"volume": -100}, {}, {}), ({"rate": 0}, {}, {}),
                                 ({"volume": "x"}, {}, {}), ({"qa_share": True}, {}, {}),
                                 ({"human_err_rate": 1.2}, {}, {}), ({"fee_per_closed": -1}, {}, {}),
                                 ({}, {"contained": (0.9, 0.4)}, {}), ({}, {"contained": (0.4,)}, {}),
                                 ({}, {}, {"contained": 5}), ({}, {}, {"contained": " "})):
            try:
                validate({**DEFAULTS, **bad}, rng, ev_bad)
            except SystemExit as e:
                assert isinstance(e.code, str) and e.code  # a message, not a traceback
            else:
                raise AssertionError(f"accepted bad input {bad} {rng} {ev_bad}")
        print("\nself-check ok")
