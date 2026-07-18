# FILE: eval/extrinsic.py
"""Uses Ragas for faithfulness / answer correctness / relevance."""
from ragas import evaluate
from ragas.metrics import faithfulness, answer_correctness, answer_relevancy
from datasets import Dataset


def run_extrinsic(golden_set: list[dict], answer_fn) -> dict:
    """answer_fn(item: dict) -> {"response": str, "citations": [...]}.
    Skips items with no expected_answer (e.g. role_boundary_test items
    that intentionally probe access-denial rather than answer content --
    Ragas' ground-truth metrics aren't meaningful there)."""
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
    scores = evaluate(dataset, metrics=[faithfulness, answer_correctness, answer_relevancy])
    result = scores.to_pandas().mean(numeric_only=True).to_dict()
    result["n"] = len(rows)
    return result