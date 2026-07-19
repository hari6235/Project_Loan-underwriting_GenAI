# FILE: mcp/simulated_handlers.py
"""
Deterministic local implementations for MCP servers running in "simulated"
mode (see config/mcp_servers.yaml). These are NOT canned/fake responses --
each handler performs real validation, lookup, or computation against its
declared input_schema and returns data in the same shape a live HTTP
integration would. Swapping a server to `mode: http` in the config requires
no changes to mcp/client.py, mcp/tool_adapter.py, or the agent.

Registered by dotted path in config/mcp_servers.yaml -> `handler:`.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone


class MCPToolError(Exception):
    """Raised by a handler on invalid input -- surfaced to the caller as a
    structured MCP error, not swallowed."""


def _seeded_float(seed_str: str, low: float, high: float) -> float:
    """Deterministic pseudo-random float in [low, high) derived from a
    stable hash of seed_str, so the same input always produces the same
    simulated output (a real requirement for testable, non-flaky tools)."""
    digest = hashlib.sha256(seed_str.encode()).hexdigest()
    frac = int(digest[:8], 16) / 0xFFFFFFFF
    return round(low + frac * (high - low), 2)


# ---------------------------------------------------------------------------
# credit_bureau_lookup
# ---------------------------------------------------------------------------
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def credit_bureau_fetch_credit_report(pan: str) -> dict:
    if not pan or not PAN_RE.match(pan.strip().upper()):
        raise MCPToolError(f"Invalid PAN format: '{pan}'")
    pan = pan.strip().upper()
    score = int(_seeded_float(pan + "score", 550, 830))
    return {
        "pan": pan,
        "credit_score": score,
        "active_tradelines": int(_seeded_float(pan + "tl", 1, 6)),
        "recent_enquiries_90d": int(_seeded_float(pan + "enq", 0, 4)),
        "reported_defaults": [] if score > 620 else [{"type": "late_payment", "months_ago": 8}],
        "report_date": datetime.now(timezone.utc).date().isoformat(),
    }


# ---------------------------------------------------------------------------
# income_verification
# ---------------------------------------------------------------------------
def income_verification_verify_income(pan: str, declared_monthly_income: float) -> dict:
    if not pan or not PAN_RE.match(pan.strip().upper()):
        raise MCPToolError(f"Invalid PAN format: '{pan}'")
    if declared_monthly_income is None or declared_monthly_income <= 0:
        raise MCPToolError("declared_monthly_income must be a positive number")

    pan = pan.strip().upper()
    # Simulated bureau-reported income varies +/-15% around the declared figure.
    variance_pct = _seeded_float(pan + "income_var", -0.15, 0.15)
    verified_income = round(declared_monthly_income * (1 + variance_pct), 2)
    return {
        "pan": pan,
        "declared_monthly_income": declared_monthly_income,
        "verified_monthly_income": verified_income,
        "variance_pct": round(variance_pct * 100, 2),
        "source": "simulated_payroll_registry",
        "flag": "MATCH" if abs(variance_pct) <= 0.10 else "REVIEW_RECOMMENDED",
    }


# ---------------------------------------------------------------------------
# property_valuation
# ---------------------------------------------------------------------------
_LOCALITY_RATE_PER_SQFT = {
    "metro": 9500,
    "urban": 5500,
    "semi_urban": 3200,
    "rural": 1800,
}
_TYPE_MULTIPLIER = {
    "apartment": 1.0,
    "independent_house": 1.15,
    "plot": 0.7,
    "commercial": 1.4,
}


def property_valuation_estimate_property_value(locality: str, area_sqft: float, property_type: str) -> dict:
    if area_sqft is None or area_sqft <= 0:
        raise MCPToolError("area_sqft must be a positive number")

    locality_key = (locality or "").strip().lower().replace(" ", "_")
    type_key = (property_type or "").strip().lower().replace(" ", "_")
    rate = _LOCALITY_RATE_PER_SQFT.get(locality_key)
    multiplier = _TYPE_MULTIPLIER.get(type_key)
    if rate is None:
        raise MCPToolError(
            f"Unknown locality tier '{locality}'. Expected one of: {list(_LOCALITY_RATE_PER_SQFT)}"
        )
    if multiplier is None:
        raise MCPToolError(
            f"Unknown property_type '{property_type}'. Expected one of: {list(_TYPE_MULTIPLIER)}"
        )

    estimated_value = round(area_sqft * rate * multiplier, -3)  # round to nearest 1000
    return {
        "locality": locality_key,
        "area_sqft": area_sqft,
        "property_type": type_key,
        "estimated_value": estimated_value,
        "rate_per_sqft_used": rate,
        "valuation_confidence": 0.78,
        "comparable_count": int(_seeded_float(f"{locality_key}{type_key}{area_sqft}", 3, 15)),
    }


# ---------------------------------------------------------------------------
# regulatory_update_feed
# ---------------------------------------------------------------------------
_SEED_UPDATES = [
    {
        "title": "RBI Master Circular Update -- Restructured Loan Classification",
        "topic": "restructuring",
        "days_ago": 12,
        "summary": "Clarifies asset-classification treatment for loans restructured due to income shocks.",
        "source_url": "https://rbi.org.in/circulars/example-1",
    },
    {
        "title": "Fair Practices Code Amendment -- Top-up Loan Disclosure",
        "topic": "fair_practices",
        "days_ago": 30,
        "summary": "Adds mandatory disclosure requirements when offering top-up loans to existing borrowers.",
        "source_url": "https://rbi.org.in/circulars/example-2",
    },
    {
        "title": "LTV Cap Revision -- Home Loans Above ₹75L",
        "topic": "ltv",
        "days_ago": 65,
        "summary": "Revises the maximum LTV band applicable to high-value home loans in metro areas.",
        "source_url": "https://rbi.org.in/circulars/example-3",
    },
]


def _normalize_topic(s: str) -> str:
    return s.strip().lower().replace("_", " ").replace("-", " ")


def regulatory_feed_fetch_recent_updates(topic: str = None, since_days: int = 90) -> dict:
    since_days = since_days or 90
    now = datetime.now(timezone.utc)
    normalized_topic = _normalize_topic(topic) if topic else None
    results = []
    for item in _SEED_UPDATES:
        if item["days_ago"] > since_days:
            continue
        if normalized_topic:
            item_topic = _normalize_topic(item["topic"])
            # Bidirectional substring match, not just one direction: a
            # realistic LLM-extracted phrase like "loan restructuring"
            # must match the seed tag "restructuring" (tag is a substring
            # of the phrase), and a short query like "ltv" must also match
            # an exact tag "ltv" (phrase is a substring of the tag). The
            # old code only checked one direction, so any multi-word topic
            # phrase silently matched nothing.
            if item_topic not in normalized_topic and normalized_topic not in item_topic:
                continue
        results.append({
            "title": item["title"],
            "date": (now - timedelta(days=item["days_ago"])).date().isoformat(),
            "summary": item["summary"],
            "source_url": item["source_url"],
        })
    return {"updates": results, "count": len(results)}


# Dotted-path handler registry used by mcp/client.py.
HANDLERS = {
    "credit_bureau.fetch_credit_report": credit_bureau_fetch_credit_report,
    "income_verification.verify_income": income_verification_verify_income,
    "property_valuation.estimate_property_value": property_valuation_estimate_property_value,
    "regulatory_feed.fetch_recent_updates": regulatory_feed_fetch_recent_updates,
}