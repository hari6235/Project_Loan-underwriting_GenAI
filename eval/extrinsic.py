# FILE: eval/extrinsic.py
"""Uses Ragas for faithfulness / answer correctness / relevance.

The `ragas` import is deliberately done INSIDE run_extrinsic(), not at
module load time. ragas has a history of breaking on import when paired
with a newer langchain-community than it expects (it still imports
ChatVertexAI from a path langchain-community later removed -- see
requirements.txt's pinned langchain versions for the real fix). Importing
lazily means that if this ever breaks again in some environment, only
this one metric degrades (returns None with an error note) instead of
crashing eval/run_eval.py -> eval/regression_suite.py -> eval/dashboard.py
-> the entire Streamlit app, since all of those import this module
transitively at load time.
"""


def run_extrinsic(golden_set: list[dict], answer_fn) -> dict:
    """answer_fn(item: dict) -> {"response": str, "citations": [...]}.
    Skips items with no expected_answer (e.g. role_boundary_test items
    that intentionally probe access-denial rather than answer content --
    Ragas' ground-truth metrics aren't meaningful there)."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_correctness, answer_relevancy
        from datasets import Dataset
    except Exception as exc:
        return {
            "faithfulness": None,
            "answer_correctness": None,
            "answer_relevancy": None,
            "n": 0,
            "error": f"ragas unavailable: {exc}",
        }

    rows = []
    for item in golden_set:
        if not item.get("expected_answer"):
            continue
        result = answer_fn(item)
        rows.append({
            "question": item["query"],
            "answer": result["response"],
            "contexts": [c.get("text", "") for c in result.get("citations", [])] or [""],
            "ground_truth": item["expected_answer"],
        })
    if not rows:
        return {"faithfulness": None, "answer_correctness": None, "answer_relevancy": None, "n": 0}

    dataset = Dataset.from_list(rows)
    try:
        # raise_exceptions=False: a single row/metric failing inside ragas's
        # internal thread runner (e.g. a transient OpenAI API error, a rate
        # limit, or a malformed row) must not crash the whole regression run
        # -- ragas records NaN for that cell instead and keeps going. This is
        # literally what ragas's own ExceptionInRunner error message
        # recommends. We still don't know the ROOT CAUSE of any individual
        # failure this way (ragas logs a per-row warning to the console, not
        # to this return value), so check your terminal/server logs for
        # "Exception raised in Job" warnings if scores come back much lower
        # than expected -- that tells you which underlying error to fix
        # (commonly: API key / rate limit / model access issues).
        scores = evaluate(
            dataset,
            metrics=[faithfulness, answer_correctness, answer_relevancy],
            raise_exceptions=False,
        )
    except Exception as exc:
        return {
            "faithfulness": None,
            "answer_correctness": None,
            "answer_relevancy": None,
            "n": len(rows),
            "error": f"ragas evaluate() failed: {exc}",
        }

    df = scores.to_pandas()
    means = df.mean(numeric_only=True, skipna=True).to_dict()
    # NaN (all-failed column, or ragas's per-row failure marker) -> None,
    # so this stays clean JSON and doesn't silently fail threshold checks
    # in eval/regression_suite.py (NaN >= threshold is always False, which
    # would misleadingly show as "failed" rather than "not measured").
    result = {k: (None if v != v else v) for k, v in means.items()}  # v != v is the NaN check
    result["n"] = len(rows)
    result["n_failed_rows"] = int(df.isna().any(axis=1).sum()) if not df.empty else 0
    return result