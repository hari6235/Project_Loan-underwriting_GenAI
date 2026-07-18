# FILE: eval/llm_judge.py
"""LLM-as-judge scoring using a model from a DIFFERENT family than the
generation model (Anthropic Claude judging OpenAI-generated answers, per
the 'same model for generation + judging' pitfall). The judge model is
configurable via LLM_JUDGE_MODEL rather than hardcoded.

Defaults to Haiku (Anthropic's cheap/fast tier) rather than Opus --
Haiku is still a different model family from the gpt-4o-mini generation
model, so the "don't self-judge" property this exists for is preserved,
just at a fraction of the cost. Bump LLM_JUDGE_MODEL to a stronger model
(e.g. claude-opus-4-8) only for a final, one-time formal evaluation run
where judging quality matters more than per-run cost."""
import json
import os

import anthropic

JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", "claude-haiku-4-5-20251001")

JUDGE_PROMPT = """Rate this RAG answer on four dimensions, 1-5 each: Correctness, Completeness, Citation Quality, Clarity.
Question: {question}
Answer: {answer}
Expected: {expected}
Return ONLY JSON, no markdown fences, no commentary: {{"correctness": int, "completeness": int, "citation_quality": int, "clarity": int}}"""


def judge(question: str, answer: str, expected: str) -> dict:
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(question=question, answer=answer, expected=expected)}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text)


def run_llm_judge(golden_set: list[dict], answer_fn) -> dict:
    """answer_fn(item: dict) -> {"response": str, ...}. Skips items with no
    expected_answer for the same reason as run_extrinsic."""
    scores = {"correctness": [], "completeness": [], "citation_quality": [], "clarity": []}
    failures = 0
    for item in golden_set:
        if not item.get("expected_answer"):
            continue
        result = answer_fn(item)
        try:
            s = judge(item["query"], result["response"], item["expected_answer"])
            for k in scores:
                scores[k].append(s[k])
        except Exception:
            failures += 1
    out = {k: (sum(v) / len(v) if v else None) for k, v in scores.items()}
    out["n"] = len(scores["correctness"])
    out["judge_failures"] = failures
    out["judge_model"] = JUDGE_MODEL
    return out