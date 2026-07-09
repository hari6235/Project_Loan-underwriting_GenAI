# FILE: eval/extrinsic.py
"""Uses Ragas for faithfulness / answer correctness / relevance."""
from ragas import evaluate
from ragas.metrics import faithfulness, answer_correctness, answer_relevancy
from datasets import Dataset


def run_extrinsic(golden_set: list[dict], answer_fn) -> dict:
    rows = []
    for item in golden_set:
        result = answer_fn(item["query"], item.get("history", []))
        rows.append({
            "question": item["query"],
            "answer": result["response"],
            "contexts": [c["text"] for c in result["citations"]],
            "ground_truth": item["expected_answer"],
        })
    dataset = Dataset.from_list(rows)
    scores = evaluate(dataset, metrics=[faithfulness, answer_correctness, answer_relevancy])
    return scores.to_pandas().mean(numeric_only=True).to_dict()