# FILE: tools/router.py

from tools.credit_score_tool import credit_score_analyzer
from tools.dti_tool import dti_calculator
from tools.document_tool import document_verification
from tools.advanced_tools import (
    max_loan_by_credit_score,
    topup_eligibility,
    max_allowed_emi,
    solve_tenure_for_emi,
    simulate_rate_comparison,
)
from tools.parse_values import (
    extract_credit_score,
    extract_income_and_emi,
    extract_liabilities,
    extract_pan,
    extract_aadhaar,
    extract_principal,
    extract_tenure_months,
    extract_all_rates,
    extract_first_rate,
)
from tools.id_extractor import extract_all_applicant_ids
from tools.context_resolver import resolve_applicant
from tools.rag_tool import knowledge_retrieval
from rag.contextualizer import contextualize_query
from data.applicant_store import get_applicant
from utils.logger import get_logger

logger = get_logger("tools.router")

# Strong, RAG-only signals: phrases that indicate a document/policy/past-case
# lookup and essentially never appear in a genuine calculation request. These
# are checked BEFORE any deterministic branch, so a query like "find prior
# underwriting memos where co-applicant income brought DTI below threshold"
# routes to RAG instead of being intercepted by the DTI branch just because
# it happens to mention "DTI".
STRONG_KNOWLEDGE_SIGNALS = [
    "prior case", "past case", "similar profile", "prior underwriting",
    "memo", "memos", "master circular", "fair practices",
]

# Softer signals: still checked, but only as a fallback if nothing else
# matched -- these CAN legitimately co-occur with a tool query (e.g. "as per
# current underwriting policy" alongside a DTI/credit-score ask), so they
# stay last instead of pre-empting deterministic branches.
KNOWLEDGE_KEYWORDS = [
    "policy", "circular", "rbi", "regulation", "regulatory", "clause",
    "guideline", "ltv",
]


def tool_router(query: str, history: list = None):
    query_lower = query.lower()
    history = history or []

    # -------------------- KNOWLEDGE RETRIEVAL (STRONG SIGNALS FIRST) --------------------
    if any(sig in query_lower for sig in STRONG_KNOWLEDGE_SIGNALS):
        logger.info("Routing to knowledge_retrieval (strong signal) for query: %.60s", query)
        return knowledge_retrieval(query, history=history)

    # -------------------- COMPARE APPLICANTS --------------------
    if "compare" in query_lower and ("applicant" in query_lower or "risk profile" in query_lower):
        ids = extract_all_applicant_ids(query)
        if len(ids) >= 2:
            records = [get_applicant(i) for i in ids]
            if all(records):
                comparison = []
                for rec in records:
                    comparison.append({
                        "applicant_id": rec["applicant_id"],
                        "credit_score_assessment": credit_score_analyzer(rec["credit_score"]),
                        "dti_assessment": dti_calculator(rec["monthly_income"], rec["emi"]),
                    })
                logger.info("Routing to applicant comparison for %s", ids)
                return {"type": "comparison_response", "comparison": comparison}
            missing = [i for i, r in zip(ids, records) if not r]
            return {
                "type": "clarification_needed",
                "message": f"I couldn't find records for: {', '.join(missing)}. Please check the applicant IDs.",
            }

    # -------------------- MAX LOAN FROM CREDIT SCORE --------------------
    if "loan" in query_lower and ("max" in query_lower or "maximum" in query_lower) and (
        "credit score" in query_lower or "cibil" in query_lower
    ):
        score = extract_credit_score(query)
        if score is None:
            return {
                "type": "clarification_needed",
                "message": "Please share the credit score (e.g. '680') so I can estimate the indicative maximum loan amount.",
            }
        logger.info("Routing to max_loan_by_credit_score(score=%d)", score)
        return max_loan_by_credit_score(score)

    # -------------------- RISK FLAG EXPLANATION --------------------
    if "flagged" in query_lower or "risk factor" in query_lower or "why was" in query_lower:
        applicant = resolve_applicant(query, history)
        if applicant:
            flags = applicant.get("risk_flags", [])
            label = applicant.get("applicant_id") or applicant.get("application_id")
            if not flags:
                return {
                    "type": "tool_response",
                    "response": f"No risk flags recorded for {label}; stored data currently looks low-risk.",
                }
            shown = flags[:3] if "three" in query_lower else flags
            logger.info("Returning stored risk flags for %s", label)
            return {"type": "tool_response", "applicant_id": label, "risk_flags": shown}
        return {
            "type": "clarification_needed",
            "message": "Please share the applicant or application ID (e.g. 'application #3310') so I can pull the recorded risk factors.",
        }

    # -------------------- SALARY REVISION / RE-RUN --------------------
    if "salary revision" in query_lower or "re-run" in query_lower or "rerun" in query_lower:
        applicant = resolve_applicant(query, history)
        if not applicant:
            return {
                "type": "clarification_needed",
                "message": "Which applicant should I re-run underwriting for? Please share the applicant/application ID.",
            }
        new_income, _ = extract_income_and_emi(query)
        if new_income is None:
            return {
                "type": "clarification_needed",
                "message": "Please share the revised income figure (e.g. 'salary revision to 15L').",
            }
        label = applicant.get("applicant_id") or applicant.get("application_id")
        logger.info("Re-running underwriting for %s with revised income", label)
        return {
            "type": "tool_response",
            "applicant_id": label,
            "revised_monthly_income": round(new_income, 2),
            "dti_assessment": dti_calculator(new_income, applicant["emi"]),
            "credit_score_assessment": credit_score_analyzer(applicant["credit_score"]),
        }

    # -------------------- TOP-UP ELIGIBILITY --------------------
    if "top-up" in query_lower or "topup" in query_lower or "top up" in query_lower:
        applicant = resolve_applicant(query, history)
        _, emi_from_text = extract_income_and_emi(query)
        income = applicant["monthly_income"] if applicant else None
        emi = emi_from_text if emi_from_text is not None else (applicant["emi"] if applicant else None)
        if income is None or emi is None:
            return {
                "type": "clarification_needed",
                "message": "Please share the applicant's monthly income and existing EMI (or applicant ID) so I can check top-up eligibility.",
            }
        logger.info("Routing to topup_eligibility(income=%.2f, emi=%.2f)", income, emi)
        return topup_eligibility(income, emi)

    # -------------------- TENURE FOR TARGET DTI --------------------
    if "tenure" in query_lower and ("%" in query_lower or "below" in query_lower or "reduce" in query_lower):
        applicant = resolve_applicant(query, history)
        income = applicant["monthly_income"] if applicant else None
        if income is None:
            return {
                "type": "clarification_needed",
                "message": "Please share the applicant's monthly income (or applicant ID) so I can calculate the EMI cap.",
            }
        cap = max_allowed_emi(income, target_dti=0.4)
        principal = extract_principal(query)
        rate = extract_first_rate(query)
        if principal and rate:
            logger.info("Solving tenure for EMI cap using principal/rate from query")
            return {"type": "tool_response", **cap, "tenure_result": solve_tenure_for_emi(principal, rate, cap["max_allowed_emi"])}
        return {
            "type": "tool_response",
            **cap,
            "note": "Share the loan principal and interest rate to compute the exact tenure needed to stay under this EMI cap.",
        }

    # -------------------- RATE SIMULATION --------------------
    if "simulate" in query_lower and ("interest rate" in query_lower or "%" in query_lower):
        rates = extract_all_rates(query)
        principal = extract_principal(query)
        tenure = extract_tenure_months(query)
        if not (rates and principal and tenure):
            missing = []
            if not principal:
                missing.append("loan principal")
            if not tenure:
                missing.append("tenure (months or years)")
            if not rates:
                missing.append("interest rate(s) to compare")
            return {
                "type": "clarification_needed",
                "message": f"Please share the {', '.join(missing)} so I can simulate the EMI at each rate.",
            }
        logger.info("Routing to simulate_rate_comparison(rates=%s)", rates)
        return simulate_rate_comparison(principal, tenure, rates)

    # -------------------- CREDIT SCORE (by ID or raw number) --------------------
    if "credit score" in query_lower or "cibil" in query_lower:
        applicant = resolve_applicant(query, history)
        if applicant:
            result = credit_score_analyzer(applicant["credit_score"])
            result["applicant_id"] = applicant.get("applicant_id") or applicant.get("application_id")
            logger.info("Routing to credit_score_analyzer via applicant record %s", result["applicant_id"])
            return result

        score = extract_credit_score(query)
        if score is None:
            return {
                "type": "clarification_needed",
                "message": "Please share the applicant's credit score or applicant ID (e.g. 'credit score 720' or 'applicant A-101') so I can assess it.",
            }
        logger.info("Routing to credit_score_analyzer(score=%d)", score)
        return credit_score_analyzer(score)

    # -------------------- DTI / EMI / LIABILITIES --------------------
    if "dti" in query_lower or "emi" in query_lower or "debt" in query_lower or "liabilit" in query_lower:
        income, emi = extract_income_and_emi(query)
        liabilities = extract_liabilities(query)

        if emi is None and liabilities is not None:
            logger.info("DTI tool matched liabilities but no EMI.")
            return {
                "type": "clarification_needed",
                "message": (
                    "I have the total liabilities figure, but DTI needs the monthly "
                    "EMI (installment amount), not the outstanding loan/liability total — "
                    "those aren't interchangeable without knowing tenure and interest rate. "
                    "Could you share the monthly EMI instead? (e.g. 'EMI 20000')"
                ),
            }

        missing = [name for name, val in (("monthly income", income), ("EMI", emi)) if val is None]
        if missing:
            logger.info("DTI tool matched but missing: %s", missing)
            return {
                "type": "clarification_needed",
                "message": (
                    f"Please share the applicant's {' and '.join(missing)} "
                    f"(e.g. 'income 50000, EMI 15000') so I can calculate DTI."
                ),
            }

        logger.info("Routing to dti_calculator(income=%.2f, emi=%.2f)", income, emi)
        return dti_calculator(monthly_income=income, emi=emi)

    # -------------------- KYC / DOCUMENT VERIFICATION --------------------
    if (
        "kyc" in query_lower
        or "pan" in query_lower
        or "aadhaar" in query_lower
        or "document verification" in query_lower
        or "verification report" in query_lower
    ):
        applicant = resolve_applicant(query, history)
        if applicant and applicant.get("pan") and applicant.get("aadhaar"):
            result = document_verification(pan=applicant["pan"], aadhaar=applicant["aadhaar"])
            result["applicant_id"] = applicant.get("applicant_id") or applicant.get("application_id")
            logger.info("Routing to document_verification via applicant record %s", result["applicant_id"])
            return result

        pan = extract_pan(query)
        aadhaar = extract_aadhaar(query)
        missing = [name for name, val in (("PAN", pan), ("Aadhaar", aadhaar)) if val is None]
        if missing:
            logger.info("Document verification tool matched but missing: %s", missing)
            return {
                "type": "clarification_needed",
                "message": f"Please share the applicant/application ID, or the {' and '.join(missing)} number(s) directly, so I can verify KYC documents.",
            }
        logger.info("Routing to document_verification(pan=%s, aadhaar=%s)", pan, aadhaar)
        return document_verification(pan=pan, aadhaar=aadhaar)

    # -------------------- KNOWLEDGE RETRIEVAL (SOFTER SIGNALS, FALLBACK) --------------------
    if any(kw in query_lower for kw in KNOWLEDGE_KEYWORDS):
        logger.info("Routing to knowledge_retrieval (soft signal, fallback) for query: %.60s", query)
        return knowledge_retrieval(query, history=history)

    # -------------------- KNOWLEDGE RETRIEVAL (CONTEXTUAL FALLBACK) --------------------
    # Nothing matched on the RAW follow-up text. This is the elliptical-query
    # gap: something like "What about for a loan against property instead?"
    # contains none of STRONG_KNOWLEDGE_SIGNALS/KNOWLEDGE_KEYWORDS on its own
    # -- even though, resolved against the prior turn, it's clearly a policy
    # lookup -- so every branch above (including the soft-signal check just
    # above) misses it and this would otherwise fall through to the generic
    # LLM with no retrieval/citations at all.
    #
    # Only reached here (after every deterministic branch already had first
    # crack at the RAW query), and only re-checks the knowledge-retrieval
    # signals -- not the full deterministic cascade -- so a rewritten query
    # can't accidentally misfire a numeric/ID-based tool branch instead.
    if history:
        standalone_query = contextualize_query(query, history)
        if standalone_query.lower() != query_lower:
            standalone_lower = standalone_query.lower()
            if any(sig in standalone_lower for sig in STRONG_KNOWLEDGE_SIGNALS) or \
               any(kw in standalone_lower for kw in KNOWLEDGE_KEYWORDS):
                logger.info(
                    "Routing to knowledge_retrieval (contextual fallback) | original=%.60s | standalone=%.60s",
                    query, standalone_query,
                )
                return knowledge_retrieval(standalone_query, history=history)

    return None