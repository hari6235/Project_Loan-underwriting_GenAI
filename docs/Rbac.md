# Role-Based RAG (RBAC)

## Goal

Restrict document retrieval based on the authenticated user's role. In a
regulated banking context, a junior analyst should not retrieve internal
audit reports, and a customer-facing role should not surface compliance
memos — even if those chunks would otherwise be the best semantic match.

## Components

| File | Responsibility |
|---|---|
| `rbac/models.py` | Data models for roles and the permission matrix. |
| `rbac/role_registry.py` | Loads `config/roles.yaml` and exposes the role → permissions mapping. |
| `rbac/filter.py` | Pre-retrieval filter: injects role-based `doc_type` constraints into the vector store query **before** hybrid retrieval and reranking run. |
| `rbac/validator.py` | Post-retrieval validator: double-checks that no chunk with a denied `doc_type` made it into the final retrieved set (defense in depth against a filter bug). |
| `rbac/audit.py` | Writes every role-filtered retrieval to `logs/rbac_audit.jsonl` for compliance audit trails. |

## Role-permission matrix

Defined in `config/roles.yaml`. Four roles are configured (minimum required:
3), each with `allowed_doc_types` / `denied_doc_types` over the metadata
`doc_type` values chunks are tagged with at ingest time
(`policy | circular | memo | audit`):

| Role | Allowed doc types | Denied doc types | Can approve HITL override |
|---|---|---|---|
| `junior_analyst` | policy, circular | audit, memo | No |
| `senior_underwriter` | policy, circular, memo | audit | No |
| `credit_head` | policy, circular, memo, audit | — | **Yes** |
| `auditor` | policy, circular, memo, audit | — | No (segregation of duties) |

Any role name **not** in the list above falls back to `default_role`, which
denies all `doc_type`s — the system fails closed, not open, for unrecognised
roles.

## Retrieval flow with RBAC

1. `api/deps.py`'s `resolve_role` dependency determines the caller's role for
   the request (from auth context — see `GET /auth/context`).
2. `rbac/filter.py` converts the role's `allowed_doc_types` into a metadata
   filter and applies it **before** `rag/retriever_bm25.py` /
   `rag/retriever_hybrid.py` run, so restricted chunks are excluded from the
   candidate set at the source, not filtered out after the fact.
3. `rag/reranker.py` reranks only the already-permitted candidate set.
4. `rbac/validator.py` runs a final check on the chunks about to be returned,
   confirming none carry a `doc_type` outside the role's `allowed_doc_types`.
   Any leak here is treated as a hard failure, not a warning.
5. `rbac/audit.py` logs the role, query, and returned `doc_type`s to
   `logs/rbac_audit.jsonl`.

## Segregation of duties

`can_request_hitl_override` is `true` only for `credit_head`. `auditor` has
full **read** access (for audit purposes) but is explicitly barred from
approving or overriding a HITL decision, enforced at the HITL review
endpoint via the resolved role — an auditor cannot both see everything and
approve exceptions.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /roles` | Lists configured roles and their permission summary. |
| `GET /auth/context` | Returns the resolved role/permissions for the current request. |

## Streamlit UI

The "Role Selector" control in `app.py` lets a user switch the active role
for the session, and the chat/document tabs immediately reflect the
resulting retrieval restrictions.

## Testing

`tests/test_role_based_rag.py` covers: pre-retrieval filter correctness per
role, the default-deny fallback for unknown roles, the post-retrieval
zero-leakage validator, and audit-log writes. The acceptance bar for this
project is **0% leakage** — any restricted chunk reaching an unauthorised
role is treated as a test failure, not a warning.

## Adding a new role

Add an entry under `roles:` in `config/roles.yaml` with its
`allowed_doc_types` / `denied_doc_types` and `can_request_hitl_override`
flag. No code changes are required — `rbac/role_registry.py` reads the YAML
at runtime, and `rbac/filter.py` / `rbac/validator.py` apply generically to
any role defined there.