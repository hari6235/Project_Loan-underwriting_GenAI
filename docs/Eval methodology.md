# Evaluation Methodology

## Goal

Extend the Week 6 evaluation harness into a production-grade regression and
monitoring suite that catches quality degradation before it reaches users,
covering both RAG-answer quality and the new Week 8 components.

## Components

| File | Responsibility |
|---|---|
| `eval/golden_set.json` | The golden question/answer/context corpus used as the ground truth for regression runs. |
| `eval/intrinsic.py` | Intrinsic RAG metrics (retrieval precision/recall, context relevance) computed directly against the golden set. |
| `eval/extrinsic.py` | Extrinsic/end-to-end metrics — answer correctness and faithfulness judged against the full pipeline output. |
| `eval/llm_judge.py` | LLM-as-judge scoring for dimensions that aren't purely retrieval-based (e.g. citation precision, domain correctness). |
| `eval/custom_metrics.py` | Domain-specific metric dimensions beyond default Ragas metrics (see below). |
| `eval/regression_suite.py` | Runs the full golden set through the live pipeline and compares results against the configured acceptance thresholds; can run on every deployment or on demand. |
| `eval/comparator.py` | Version-A vs version-B comparison mode, for evaluating the impact of a prompt or model change before rollout. |
| `eval/export.py` | Exports run results to JSON/CSV for CI pipeline integration. |
| `eval/dashboard.py` | Streamlit-rendered trend graphs over historical regression runs. |
| `eval/drift.py` | Compares current-run outputs/embeddings against a stored baseline snapshot to catch silent quality degradation (the Week 8 "drift" concern, implemented as an evaluation-suite module rather than a separate top-level package). |

## Evaluation dimensions

In addition to standard Ragas defaults (faithfulness, answer relevance,
context precision/recall), the following domain-specific dimensions are
added for this project (`eval/custom_metrics.py`):

- **Domain-specific correctness** — does the answer align with actual
  underwriting policy, not just generic plausibility.
- **Regulatory compliance** — does the answer avoid recommending anything
  that would violate a policy or regulatory constraint.
- **Citation precision** — when the answer cites a source chunk, does that
  chunk actually support the claim.

## Regression runs

1. `eval/regression_suite.py` loads `eval/golden_set.json` and runs each
   item through the live chat pipeline (RAG + tool + HITL routing, as a real
   user query would).
2. Scores are computed via `eval/intrinsic.py`, `eval/extrinsic.py`, and
   `eval/llm_judge.py`, aggregated with the custom dimensions from
   `eval/custom_metrics.py`.
3. A timestamped snapshot is written to `reports/regression_history/` (see
   e.g. `20260719T062836Z.json`), and a human-readable summary to
   `reports/eval_week4_final.md` / `reports/eval_baseline.md`.
4. `eval/comparator.py` can diff any two snapshots (e.g. before/after a
   prompt version change) to quantify regression or improvement.
5. `eval/export.py` writes the same results out as JSON/CSV for consumption
   by an external CI pipeline.

## Drift detection

`eval/drift.py` and the `POST /eval/drift` endpoint compare the current
run's answer/embedding distribution against a stored baseline snapshot,
flagging cases where output quality has silently degraded (e.g. after a
model or embedding version change) without a corresponding code change.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `POST /eval/regression` | Triggers a full regression run against the golden set and returns/stores the result. |
| `POST /eval/drift` | Runs a drift check against the stored baseline. |

## Streamlit UI

The "Eval Dashboard" tab in `app.py` (backed by `eval/dashboard.py`) plots
trend graphs across `reports/regression_history/` runs, so a reviewer can
see quality trending over time rather than only a single pass/fail snapshot.

## Testing

Regression correctness is validated by running `eval/regression_suite.py`
against the golden set and checking output against the acceptance
thresholds defined for this project (see the Week 8 problem statement,
Section 4). CI is expected to run this suite on every deployment via
`eval/export.py`'s JSON/CSV output.