# FILE: eval/run_eval.py
import json
import os
from eval.intrinsic import run_intrinsic
from eval.extrinsic import run_extrinsic
from eval.llm_judge import run_llm_judge
from tools.rag_tool import knowledge_retrieval
from rag.state import embedder, vector_store, bm25_retriever
from rag.retriever_hybrid import hybrid_search
from rag.reranker import rerank
from rag.contextualizer import contextualize_query


def retrieve_fn(query, history=None):
    """Mirrors tools/rag_tool.py's retrieval path, including query
    contextualization. Without this, intrinsic metrics (Hit@K/MRR) would
    score multi-turn golden-set items against the raw, un-contextualized
    fragment instead of what /chat actually retrieves for a follow-up."""
    standalone_query = contextualize_query(query, history or [])
    candidates = hybrid_search(standalone_query, vector_store, bm25_retriever, embedder, k=10)
    return rerank(standalone_query, candidates, top_k=5)


def answer_fn(query, history=None):
    return knowledge_retrieval(query, history=history or [])


def run_full_eval():
    with open("eval/golden_set.json") as f:
        golden_set = json.load(f)

    results = {
        "intrinsic": run_intrinsic(golden_set, retrieve_fn),
        "extrinsic": run_extrinsic(golden_set, answer_fn),
        "llm_judge": run_llm_judge(golden_set, answer_fn),
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/eval_baseline.md", "w") as f:
        f.write(f"# Eval Results\n\n```json\n{json.dumps(results, indent=2)}\n```")

    return results