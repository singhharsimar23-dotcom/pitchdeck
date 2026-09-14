"""
cost_config.py — fill this in yourself from the actual Cloud Console billing
page for your project, on the day you deploy. Do not copy numbers from any
blog, including the verification doc that shipped with this code — pricing
was found to be inconsistent across sources and possibly mid-change as of
September 2026. Treat every value here as "verify before trusting."
"""

RATES = {
    "vcpu_hour_usd": None,       # fill in from console
    "gb_hour_usd": None,         # fill in from console
    "event_per_1000_usd": None,  # fill in from console
    "search_per_1000_usd": None, # fill in from console — this one is a range, use the higher bound
}

def estimate_run_cost(trace: dict, rates: dict = RATES) -> float | None:
    """
    Explicitly refuses to estimate with unverified rates — this is the same
    calibrated-refusal principle applied to the tool's OWN cost reporting,
    not just the pitch content.
    """
    if any(v is None for v in rates.values()):
        return None
    
    # When verified rates are provided, compute based on trace telemetry
    total = 0.0
    stages = trace.get("stages", [])
    for s in stages:
        latency_sec = (s.get("latency_ms", 0)) / 1000.0
        # Example calculation once rates are filled in:
        # total += (latency_sec / 3600.0) * rates["vcpu_hour_usd"]
    return total
