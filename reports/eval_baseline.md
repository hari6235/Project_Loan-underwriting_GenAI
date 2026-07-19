# Eval Results

```json
{
  "n_items": {
    "total": 53,
    "rag": 13,
    "tool": 20,
    "hybrid": 20
  },
  "intrinsic": {
    "hit_rate_at_5": 0.06060606060606061,
    "mrr": 0.0,
    "n": 33
  },
  "extrinsic": {
    "faithfulness": null,
    "answer_correctness": null,
    "answer_relevancy": null,
    "n": 0,
    "error": "ragas unavailable: No module named 'langchain_community.chat_models.vertexai'"
  },
  "llm_judge": {
    "correctness": 2.8,
    "completeness": 1.3,
    "citation_quality": 3.0,
    "clarity": 5.0,
    "n": 10,
    "judge_failures": 0,
    "judge_model": "claude-haiku-4-5-20251001"
  }
}
```
