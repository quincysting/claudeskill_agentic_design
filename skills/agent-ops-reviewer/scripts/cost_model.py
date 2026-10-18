"""Per-request cost and latency model for an agent: expected value, a likely high (about p95) request,
the capped ceiling, cost per successful run, per-step share, peak load per model tier and three or four
what-ifs. Standard library only.

  python cost_model.py               # example spec (self-check runs first)
  python cost_model.py spec.json     # your spec (self-check runs first)
  python cost_model.py --selftest    # self-check only
  python cost_model.py --example     # print the example spec as JSON to edit

Merging: top-level keys you omit keep the example's values; "prices" merges per tier and per field
(override one price or add a tier without retyping the rest); "steps" replaces the example's list.

Per step: name, model (a tier in prices), p (share of requests that trigger it), calls (avg model calls
when triggered), max_calls (cap the runtime enforces; null = no cap, so the ceiling is UNBOUNDED),
tok_in / tok_out (avg tokens per call), cached / written (share of input read from / written to the
provider prompt cache), memo (share of triggers answered by your own result cache).
Optional: max_tok_in / max_tok_out (tokens per call at the cap; warned when missing on looping steps),
p95_calls / p95_tok_in (from traces; defaults 2x calls and 1.5x tok_in, flagged as assumed),
latency_s (avg seconds per call), parallel (true: the step's calls run concurrently),
stage (steps that share a stage value run concurrently; others run in sequence).
Top level: requests_per_day, peak_requests_per_day (the busiest day's volume; default: requests_per_day;
"monthly at peak" = expected $/request x this x 30), peak_hour_factor (busiest hour / average hour;
default 3: all traffic in an 8-hour day gives 24/8), retry_rate, worst_retries, other_per_request
($ of non-model cost per request, tool APIs included).
Cost per successful run (optional; printed when success_rate is set): success_rate (share of runs that met
the SLA inside guardrails), review_minutes (human review plus cleanup minutes per run, on average),
value_per_minute ($ per minute of that time). Result = (expected $/request + review_minutes x
value_per_minute) / success_rate. A user spec never inherits these three from the example.
Every number is a measurement from traces or an assumption to replace with one.
"""
import json
import math
import sys

EXAMPLE = {
    # List prices read 2026-10-06 from platform.claude.com/docs/en/about-claude/pricing. Recheck before use.
    # $/MTok. cache_read and cache_write are multipliers on that tier's own input price.
    "prices_as_of": "2026-10-06",
    "prices": {
        "small":    {"model": "Claude Haiku 4.5",  "in": 1.00,  "out": 5.00,  "cache_read": 0.10,  "cache_write": 1.25},
        "mid":      {"model": "Claude Sonnet 5.5", "in": 2.00,  "out": 10.00, "cache_read": 0.10,  "cache_write": 1.25},
        "large":    {"model": "Claude Opus 5.5",   "in": 4.00,  "out": 20.00, "cache_read": 0.05,  "cache_write": 1.25},
        "frontier": {"model": "Claude Fable 5.1",  "in": 10.00, "out": 50.00, "cache_read": 0.025, "cache_write": 1.25},
    },
    "requests_per_day": 10_000,
    "peak_requests_per_day": 25_000,
    "peak_hour_factor": 3.0,
    "retry_rate": 0.05,         # expected extra calls from retries and repairs, as a share
    "worst_retries": 2,         # retries per call the policy allows (ceiling)
    "other_per_request": 0.002, # $ for embeddings, vector queries, paid tools, eval sampling
    "success_rate": 0.85,       # runs that met the SLA inside guardrails (from evals or the SLA report)
    "review_minutes": 0.5,      # human review and cleanup per run, averaged over all runs
    "value_per_minute": 0.6667, # $40 an hour; rough is fine if it stays consistent
    "steps": [
        {"name": "router", "model": "small", "p": 1.00, "calls": 1, "max_calls": 1,
         "tok_in": 3_000, "tok_out": 50, "cached": 0.8, "latency_s": 0.6},
        {"name": "retrieval", "model": "small", "p": 0.80, "calls": 1, "max_calls": 2,
         "tok_in": 2_000, "tok_out": 100, "cached": 0.5, "memo": 0.25, "max_tok_in": 3_000,
         "max_tok_out": 300, "latency_s": 0.8},
        {"name": "reasoning", "model": "mid", "p": 0.70, "calls": 3, "max_calls": 12,
         "tok_in": 12_000, "tok_out": 400, "cached": 0.7, "max_tok_in": 40_000, "max_tok_out": 2_000,
         "p95_calls": 8, "p95_tok_in": 24_000, "latency_s": 4.0},
        {"name": "reflection", "model": "mid", "p": 0.25, "calls": 2, "max_calls": 4,
         "tok_in": 8_000, "tok_out": 300, "cached": 0.6, "max_tok_in": 16_000, "max_tok_out": 1_000,
         "latency_s": 3.0},
        {"name": "guardrails", "model": "small", "p": 1.00, "calls": 2, "max_calls": 2,
         "tok_in": 1_500, "tok_out": 20, "cached": 0.8, "max_tok_in": 1_500, "max_tok_out": 50,
         "latency_s": 0.4},
    ],
}


SUCCESS_KEYS = ("success_rate", "review_minutes", "value_per_minute")


def merge(base, user):
    spec = {**base, **{k: v for k, v in user.items() if k != "prices"}}
    if user:  # never inherit the example's success rate or review time
        for k in SUCCESS_KEYS:
            if k not in user:
                spec.pop(k, None)
    spec["prices"] = {t: dict(v) for t, v in base["prices"].items()}
    for tier, fields in user.get("prices", {}).items():
        spec["prices"][tier] = {**spec["prices"].get(tier, {}), **fields}
    if "requests_per_day" in user and "peak_requests_per_day" not in user:
        spec["peak_requests_per_day"] = user["requests_per_day"]  # never inherit the example's peak
    if "prices" in user and "prices_as_of" not in user:
        spec["prices_as_of"] = "UNDATED: you edited prices; add prices_as_of"
    return spec


def call_cost(spec, s, cached, written, tok_in, tok_out):
    pr = spec["prices"][s["model"]]
    fresh = max(0.0, 1 - cached - written)
    billed_in = tok_in * (fresh + cached * pr["cache_read"] + written * pr["cache_write"])
    return (billed_in * pr["in"] + tok_out * pr["out"]) / 1e6


def exp_calls(s):
    return s["p"] * (1 - s.get("memo", 0.0)) * s["calls"]


def step_cost(spec, s):
    return exp_calls(s) * call_cost(spec, s, s.get("cached", 0.0), s.get("written", 0.0), s["tok_in"], s["tok_out"])


def expected(spec, steps=None):
    model = sum(step_cost(spec, s) for s in (steps or spec["steps"]))
    return model * (1 + spec["retry_rate"]) + spec.get("other_per_request", 0.0)


def per_success(spec, cost):
    """Cost per successful run: (cost per run + review minutes x value per minute) / success rate."""
    if not spec.get("success_rate"):
        return None
    review = spec.get("review_minutes", 0.0) * spec.get("value_per_minute", 0.0)
    return (cost + review) / spec["success_rate"]


def heavy_step(s):
    """Heavy request (about p95): the step fires at its p95 calls and input size; cache and memo as normal."""
    cap = s["max_calls"] if s["max_calls"] is not None else math.inf
    calls = s.get("p95_calls", min(cap, 2 * s["calls"]))
    tok_in = s.get("p95_tok_in", min(s.get("max_tok_in", math.inf), 1.5 * s["tok_in"]))
    return {**s, "p": 1.0, "calls": calls, "tok_in": tok_in}


def heavy(spec):
    return expected(spec, [heavy_step(s) for s in spec["steps"]])


def ceiling(spec):
    """Every step fires at its cap, no cache, every call retried to the policy limit. A bound, not a forecast."""
    if any(s["max_calls"] is None for s in spec["steps"]):
        return None
    model = sum(s["max_calls"] * call_cost(spec, s, 0.0, 0.0, s.get("max_tok_in", s["tok_in"]),
                                           s.get("max_tok_out", s["tok_out"])) for s in spec["steps"])
    return model * (1 + spec["worst_retries"]) + spec.get("other_per_request", 0.0)


def latency(steps, retries, at_cap=False):
    """Steps run in sequence unless they share a stage; a stage takes as long as its slowest step.
    A parallel step's calls overlap, so it costs one call's latency whenever it fires."""
    stages = {}
    for i, s in enumerate(steps):
        if "latency_s" in s:
            fires = 1.0 if at_cap else s["p"] * (1 - s.get("memo", 0.0))
            n = s["max_calls"] if at_cap else s["calls"]
            t = s["latency_s"] * fires * (1 if s.get("parallel") else n) * (1 + retries)
            key = s.get("stage", f"#{i}")
            stages[key] = max(stages.get(key, 0.0), t)
    return sum(stages.values()) if stages else None


def peak_load(spec):
    rpm = spec.get("peak_requests_per_day", spec["requests_per_day"]) / 1440 * spec.get("peak_hour_factor", 3.0)
    load = {}
    for s in spec["steps"]:
        c = rpm * exp_calls(s) * (1 + spec["retry_rate"])
        t = load.setdefault(s["model"], [0.0, 0.0, 0.0])
        t[0] += c
        t[1] += c * s["tok_in"] * (1 - s.get("cached", 0.0))  # uncached + written: what most Claude ITPM limits count
        t[2] += c * s["tok_out"]
    return rpm, load


def churned(steps):
    """Prefix changes per request (timestamp, request ID before the cache point): every read becomes a write."""
    return [{**s, "cached": 0.0, "written": s.get("cached", 0.0) + s.get("written", 0.0)} for s in steps]


def what_ifs(spec):
    steps = spec["steps"]
    churn = {}
    if any(s.get("cached", 0.0) for s in steps):
        cache = ("prompt cache off", [{**s, "cached": 0.0, "written": 0.0} for s in steps])
        churn = {"prompt cache churning (every cached token written, none read)": expected(spec, churned(steps))}
    else:  # nothing cached yet: show the stable-prefix case, 80% of input read and 5% written
        cache = ("prompt cache on (80% read, 5% written)", [{**s, "cached": 0.8, "written": 0.05} for s in steps])
    cheapest = min(spec["prices"], key=lambda m: spec["prices"][m]["in"] + spec["prices"][m]["out"])
    top = max(steps, key=lambda s: step_cost(spec, s))
    return {
        cache[0]: expected(spec, cache[1]),
        **churn,
        f"BOUND, not a plan: all steps on '{cheapest}' (no quality or repair cost)":
            expected(spec, [{**s, "model": cheapest} for s in steps]),
        f"'{top['name']}' calls halved": expected(spec, [{**s, "calls": s["calls"] / 2} if s is top else s
                                                      for s in steps]),
    }


def validate(spec):
    need = ("name", "model", "p", "calls", "max_calls", "tok_in", "tok_out")
    for s in spec["steps"]:
        missing = [k for k in need if k not in s]
        if missing:
            sys.exit(f"step {s.get('name', '?')}: missing {missing}")
        if s["model"] not in spec["prices"]:
            sys.exit(f"step {s['name']}: model '{s['model']}' has no entry in prices")
        if not 0 <= s["p"] <= 1 or (s["max_calls"] is not None and s["calls"] > s["max_calls"]):
            sys.exit(f"step {s['name']}: need 0 <= p <= 1 and calls <= max_calls")
        if s.get("cached", 0) + s.get("written", 0) > 1:
            sys.exit(f"step {s['name']}: cached + written must be <= 1")
    for tier, pr in spec["prices"].items():
        if any(k not in pr for k in ("in", "out", "cache_read", "cache_write")):
            sys.exit(f"prices.{tier}: need in, out, cache_read, cache_write")
    if "success_rate" in spec and not 0 < spec["success_rate"] <= 1:
        sys.exit("success_rate: need 0 < success_rate <= 1")
    if spec.get("review_minutes", 0) < 0 or (spec.get("review_minutes") and "value_per_minute" not in spec):
        sys.exit("review_minutes: need >= 0, with value_per_minute ($ per minute) set")


def warnings(spec):
    loops = [s for s in spec["steps"] if s["max_calls"] is None or s["max_calls"] > 1]
    out = []
    for key, what in (("max_tok_in", "input"), ("max_tok_out", "output")):
        miss = [s["name"] for s in loops if key not in s]
        if miss:
            out.append(f"ceiling uses AVERAGE {what} tokens for {', '.join(miss)}: set {key} (it understates the cap)")
    guessed = [s["name"] for s in spec["steps"] if "p95_calls" not in s or "p95_tok_in" not in s]
    if guessed:
        out.append(f"likely high uses default p95 (2x calls, 1.5x input) for {', '.join(guessed)}: take p95 from traces")
    no_lat = [s["name"] for s in spec["steps"] if "latency_s" not in s]
    if no_lat and len(no_lat) < len(spec["steps"]):
        out.append(f"latency leaves out {', '.join(no_lat)}: set latency_s on every step on the request path")
    if spec.get("peak_requests_per_day", spec["requests_per_day"]) <= spec["requests_per_day"]:
        out.append("peak_requests_per_day not above requests_per_day: set the busiest day's volume, "
                   "or the peak figures equal the average")
    if "success_rate" not in spec:
        out.append("no success_rate: cost per successful run not computed; take it from evals or the SLA report")
    elif "review_minutes" not in spec:
        out.append("cost per successful run leaves out human review: set review_minutes and value_per_minute")
    uncapped = [s["name"] for s in spec["steps"] if s["max_calls"] is None]
    if uncapped:
        out.append(f"no cap on {', '.join(uncapped)}: ceiling is UNBOUNDED; rerun with proposed caps and report both")
    return out


def report(spec):
    validate(spec)
    exp, hv, ceil = expected(spec), heavy(spec), ceiling(spec)
    peak_day = spec.get("peak_requests_per_day", spec["requests_per_day"])
    cap_calls = "none" if ceil is None else sum(s["max_calls"] for s in spec["steps"])
    out = [f"prices as of {spec.get('prices_as_of', 'UNDATED: add a date')} (recheck before use)",
           f"model calls/request   expected {sum(exp_calls(s) for s in spec['steps']):.1f}   cap {cap_calls}",
           f"cost/request          expected ${exp:.4f}   likely high (~p95 request) ${hv:.4f}",
           "capped ceiling        " + ("UNBOUNDED (no cap on at least one step)" if ceil is None else
                                      f"${ceil:.4f} ({ceil / max(exp, 1e-12):.0f}x expected): every step at its cap, "
                                      "no cache, max retries; a bound, not a forecast"),
           f"per month (30 days)   ${exp * spec['requests_per_day'] * 30:,.0f} at {spec['requests_per_day']:,}/day; "
           f"${exp * peak_day * 30:,.0f} at the peak-day run rate ({peak_day:,}/day)"]
    ps = per_success(spec, exp)
    if ps is not None:
        review = ps - exp / spec["success_rate"]
        out.append(f"cost/successful run   ${ps:.4f} at {spec['success_rate']:.0%} success: model and tools "
                   f"${exp / spec['success_rate']:.4f}, human review ${review:.4f} ({review / ps:.0%})")
    out.append("share of expected cost:")
    for s in spec["steps"]:
        share = step_cost(spec, s) * (1 + spec["retry_rate"]) / exp
        out.append(f"  {s['name']:<16} {share:6.1%}   ({s['model']}, {exp_calls(s):.2f} calls)")
    if spec.get("other_per_request"):
        out.append(f"  {'other (non-model)':<16} {spec['other_per_request'] / exp:6.1%}")
    e = latency(spec["steps"], spec["retry_rate"])
    if e is not None:
        h = latency([heavy_step(s) for s in spec["steps"]], spec["retry_rate"])
        c = None if ceil is None else latency(spec["steps"], spec["worst_retries"], at_cap=True)
        out.append(f"latency               expected {e:.1f}s   likely high {h:.1f}s   ceiling "
                   + ("UNBOUNDED" if c is None else f"{c:.1f}s") + "   (staged and parallel steps overlap)")
    rpm, load = peak_load(spec)
    out.append(f"peak load ({rpm:.0f} requests/min = peak day / 1440 x peak-hour factor {spec.get('peak_hour_factor', 3.0)}):")
    for tier, (c, tin, tout) in load.items():
        out.append(f"  {tier:<9} {c:8.0f} calls/min  {tin:12,.0f} uncached input tok/min  {tout:10,.0f} output tok/min")
    out.append("what-ifs (expected $/request):")
    for name, v in what_ifs(spec).items():
        out.append(f"  {name:<66} ${v:.4f}  ({v / exp - 1:+.0%})")
    out += [f"WARNING: {w}" for w in warnings(spec)]
    return "\n".join(out)


GUIDE_SPEC = {  # fixed spec with hand-checked results; independent of EXAMPLE so EXAMPLE can change
    "prices": {"small": {"in": 1.0, "out": 5.0, "cache_read": 0.1, "cache_write": 1.25},
               "mid": {"in": 2.0, "out": 10.0, "cache_read": 0.1, "cache_write": 1.25}},
    "requests_per_day": 10_000, "retry_rate": 0.05, "worst_retries": 2, "other_per_request": 0.0,
    "steps": [
        {"name": "router", "model": "small", "p": 1.0, "calls": 1, "max_calls": 1, "tok_in": 3000, "tok_out": 50, "cached": 0.8},
        {"name": "retrieval", "model": "small", "p": 0.8, "calls": 1, "max_calls": 2, "tok_in": 2000, "tok_out": 100, "cached": 0.5, "memo": 0.25},
        {"name": "reasoning", "model": "mid", "p": 0.7, "calls": 3, "max_calls": 12, "tok_in": 12000, "tok_out": 400, "cached": 0.7},
        {"name": "reflection", "model": "mid", "p": 0.25, "calls": 2, "max_calls": 4, "tok_in": 8000, "tok_out": 300, "cached": 0.6},
        {"name": "guardrails", "model": "small", "p": 1.0, "calls": 2, "max_calls": 2, "tok_in": 1500, "tok_out": 20, "cached": 0.8},
    ],
}


def selftest():
    spec = json.loads(json.dumps(GUIDE_SPEC))
    assert abs(sum(exp_calls(s) for s in spec["steps"]) - 6.2) < 1e-9
    assert abs(expected(spec) - 0.03707) < 1e-4, expected(spec)
    assert abs(ceiling(spec) - 1.2704) < 1e-4, ceiling(spec)
    assert expected(spec) < heavy(spec) < ceiling(spec)
    off = expected(spec, [{**s, "cached": 0.0} for s in spec["steps"]])
    assert off > 2 * expected(spec)
    assert abs(expected(spec, churned(spec["steps"])) - 0.092001) < 1e-6  # hand-checked: input x (1 + 0.25 x cached)
    assert expected(spec, churned(spec["steps"])) >= off  # write multiplier >= 1: churn costs at least cache-off
    assert len(what_ifs(spec)) == 4 and len(what_ifs({**spec, "steps": [{**s, "cached": 0.0} for s in spec["steps"]]})) == 3
    spec["steps"][2]["max_calls"] = None
    assert ceiling(spec) is None and any("UNBOUNDED" in w for w in warnings(spec))
    merged = merge(EXAMPLE, {"prices": {"mid": {"in": 3.0}}})
    assert merged["prices"]["mid"]["in"] == 3.0 and merged["prices"]["mid"]["out"] == 10.0 and "small" in merged["prices"]
    assert merged["prices_as_of"].startswith("UNDATED")
    assert merge(EXAMPLE, {"requests_per_day": 500})["peak_requests_per_day"] == 500
    assert "success_rate" not in merge(EXAMPLE, {"requests_per_day": 500}) and "success_rate" in merge(EXAMPLE, {})
    spec = json.loads(json.dumps(GUIDE_SPEC))
    assert per_success(spec, expected(spec)) is None
    spec.update(success_rate=0.85, review_minutes=0.5, value_per_minute=40 / 60)  # hand-checked: $0.4358
    assert abs(per_success(spec, expected(spec)) - 0.43577) < 1e-4, per_success(spec, expected(spec))
    assert abs(per_success({**spec, "review_minutes": 0.0}, expected(spec)) - 0.04361) < 1e-4
    a = {"name": "a", "p": 1.0, "calls": 4, "max_calls": 4, "latency_s": 2.0}
    assert latency([a, {**a, "name": "b"}], 0.0) == 16.0
    assert latency([{**a, "parallel": True}, {**a, "name": "b"}], 0.0) == 10.0
    assert latency([{**a, "stage": 1}, {**a, "name": "b", "stage": 1}], 0.0) == 8.0
    assert latency([{**a, "p": 0.5, "parallel": True}], 0.0) == 1.0


if __name__ == "__main__":
    selftest()
    if sys.argv[1:2] == ["--selftest"]:
        print("self-check passed")
    elif sys.argv[1:2] == ["--example"]:
        print(json.dumps(EXAMPLE, indent=2))
    else:
        user = {}
        if sys.argv[1:]:
            with open(sys.argv[1], encoding="utf-8") as f:
                user = json.load(f)
        print(report(merge(EXAMPLE, user)))
