# FILE: eval/llm_judge.py
import json
import anthropic

JUDGE_PROMPT = """Rate this RAG answer on four dimensions, 1-5 each: Correctness, Completeness, Citation Quality, Clarity.
Question: {question}
Answer: {answer}
Expected: {expected}
Return ONLY JSON: {{"correctness": int, "completeness": int, "citation_quality": int, "clarity": int}}"""


def judge(question: str, answer: str, expected: str) -> dict:
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(question=question, answer=answer, expected=expected)}]
    )
    return json.loads(msg.content[0].text)


def run_llm_judge(golden_set: list[dict], answer_fn) -> dict:
    scores = {"correctness": [], "completeness": [], "citation_quality": [], "clarity": []}
    for item in golden_set:
        result = answer_fn(item["query"], item.get("history", []))
        s = judge(item["query"], result["response"], item["expected_answer"])
        for k in scores:
            scores[k].append(s[k])
    return {k: sum(v) / len(v) for k, v in scores.items()}