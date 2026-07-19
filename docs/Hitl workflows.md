# Human-in-the-Loop (HITL) Workflows

## Goal

Introduce approval gates at decision points where an AI recommendation
carries regulatory or credit risk and must be reviewed by a human before the
system proceeds — e.g. large loan amounts, DTI policy exceptions, or explicit
requests to override policy.

## Components

| File | Responsibility |
|---|---|
| `hitl/manager.py` | Orchestrates the HITL lifecycle: intercepts chain output, evaluates trigger rules, creates/persists review tasks, and resumes chain execution on approval/rejection. |
| `hitl/triggers.py` | Evaluates `config/hitl_rules.yaml` conditions against the current turn's `decision_context`. |
| `hitl/models.py` | Data models for a HITL task (id, rule id, severity, context snapshot, status, expiry, reviewer decision). |
| `hitl/store.py` | Persistent task store (`data/hitl_tasks.db`) so pending tasks survive process/container restarts. |

## Trigger rules

Rules live in `config/hitl_rules.yaml` and are evaluated against a
`decision_context` dict built by `chains/tool_chain.py` from **this turn's**
tool outputs, keyed by tool name (e.g.
`{"dti_calculator": {...}, "credit_score_analyzer": {...}}`).

Four rules are configured (minimum required: 3):

| Rule id | Condition | Severity |
|---|---|---|
| `high_loan_amount` | `evaluate_loan_request.loan_amount > ₹50,00,000` | high |
| `dti_policy_exception` | `dti_calculator.risk_level == "HIGH"` (DTI > 50%) | high |
| `policy_override_requested` | `flag_policy_override.flagged == true` | critical |
| `low_credit_score` | `credit_score_analyzer.credit_score < 650` | medium |

Each rule's `condition.field` first path segment **must** be a real,
registered tool name from `tools/tool_registry.py`, and the remaining
segments must match that tool's actual output keys — a field path that
doesn't correspond to a real tool call can never fire. This is enforced by a
regression test: `tests/test_hitl_workflow.py::test_all_rule_paths_resolve_to_real_tools`.

Supported operators: `gt`, `gte`, `lt`, `lte`, `eq`, `neq`, `in`, `contains`,
`exists`.

Tasks expire after `default_expiry_hours: 48` unless a rule overrides it with
its own `auto_reject_after_hours`.

## Workflow

1. `chains/tool_chain.py` runs the relevant tools for the turn and assembles
   `decision_context`.
2. `hitl/triggers.py` evaluates every rule in `config/hitl_rules.yaml`
   against that context.
3. If any rule fires, `hitl/manager.py`:
   - serialises the agent's recommendation together with full context
     (retrieved chunks, reasoning trace, tool outputs, confidence),
   - writes a task to `hitl/store.py` (`data/hitl_tasks.db`),
   - pauses the chain and returns a "pending human review" response instead
     of a final answer.
4. The task appears via `GET /hitl/pending`.
5. A human reviewer calls `POST /hitl/review/{task_id}` with an
   approve/reject decision and optional comments.
6. On approval, the original chain resumes and completes; on rejection, the
   chain returns the rejection with the reviewer's comments attached.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /hitl/pending` | Lists all pending HITL tasks. |
| `POST /hitl/review/{task_id}` | Submits an approve/reject decision for a task and resumes execution. |

## Streamlit UI

The "HITL Approvals" tab in `app.py` lists pending tasks with their full
decision context and lets a reviewer approve or reject in one click, calling
`POST /hitl/review/{task_id}` under the hood.

## Persistence

Tasks are stored in `data/hitl_tasks.db` rather than in-memory, so pending
review tasks are not lost on a process restart — a reviewer can resume
approving tasks created before a restart.

## Testing

`tests/test_hitl_workflow.py` covers: rule evaluation against synthetic
`decision_context` payloads, the field-path-to-real-tool regression guard
described above, task persistence, and the approve/reject → resume flow via
`/hitl/pending` and `/hitl/review/{task_id}`.

## Adding a new trigger rule

Add a new entry under `rules:` in `config/hitl_rules.yaml`, pointing
`condition.field` at `<real_tool_name>.<real_output_key>`. No code changes
are required — `hitl/triggers.py` reads the YAML at runtime.