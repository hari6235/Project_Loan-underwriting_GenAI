# Prompt Management (Version Control via YAML)

## Goal

Eliminate invisible prompt drift by externalising every prompt template into
versioned YAML files, so every change is tracked, diffable, auditable, and
rollbackable — no prompt strings are hardcoded in Python.

## Components

| File | Responsibility |
|---|---|
| `prompt_manager/loader.py` | Loads prompt YAML files from `prompts/` at startup, with hot-reload support (via `watchdog`) so a YAML edit is picked up without restarting the service. |
| `prompt_manager/models.py` | Data model for a prompt template: name, version, author, changelog, model compatibility, input variables, template body. |
| `prompt_manager/registry.py` | In-memory registry of all loaded prompt versions; tracks which version is "active" per prompt name. |
| `prompt_manager/validator.py` | Validates a prompt YAML against the expected schema (required fields, variable placeholders) before it's accepted into the registry. |

## Prompt files

| File | Used by |
|---|---|
| `prompts/agent_system.yaml` | Main agent system prompt (routing/tool-selection behaviour). |
| `prompts/rag_qa.yaml` | RAG answer-synthesis prompt used by `chains/rag_chain.py`. |
| `prompts/hitl_review.yaml` | Prompt used to summarise a recommendation for human review in `hitl/manager.py`. |

## YAML template structure

```yaml
name: rag_qa
version: 3
author: harisankar
model_compatibility: ["gpt-4o-mini", "claude-*"]
changelog:
  - version: 3
    note: "Tightened citation instructions to reduce hallucinated policy clauses."
  - version: 2
    note: "Added multi-turn context handling."
input_variables: [question, context, chat_history]
template: |
  You are a banking policy assistant...
```

## Runtime behaviour

1. On startup, `prompt_manager/loader.py` reads every YAML file in
   `prompts/`, validates each with `prompt_manager/validator.py`, and
   registers all versions in `prompt_manager/registry.py`, marking the
   highest version (or an explicitly pinned one) as active.
2. Chains (`chains/rag_chain.py`, `chains/tool_chain.py`, `chains/hitl_chain.py`)
   pull the **active** template for their prompt name from the registry at
   invocation time — never from a hardcoded string.
3. A filesystem watcher hot-reloads a prompt file when it changes on disk,
   re-validating before swapping it into the registry, so a bad edit does not
   take down the active prompt.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /prompts` | Lists all prompt names and their currently active version. |
| `GET /prompts/{name}/history` | Returns full version history (with changelog) for a given prompt. |
| `POST /prompts/{name}/activate` | Activates a specific prior version, i.e. a rollback, without redeploying. |

## Streamlit UI

The "Prompt Versioning" tab in `app.py` lists each prompt's version history
and changelog, and lets an operator roll back to a previous version via
`POST /prompts/{name}/activate` from the UI.

## Testing

`tests/test_prompt_versioning.py` covers: YAML schema validation,
loading/registering multiple versions, hot-reload behaviour, and the
activate/rollback endpoint switching which version chains resolve at
runtime.

## Adding or changing a prompt

1. Edit (or add) the relevant file in `prompts/`, incrementing `version` and
   adding a `changelog` entry — never edit the template string in Python.
2. The loader picks up the change automatically (hot-reload); no hardcoded
   fallback exists elsewhere in the codebase.
3. To roll back, call `POST /prompts/{name}/activate` with the earlier
   version number — the file for that version is retained in `prompts/` (via
   the changelog/version history), so history is never lost.