# LangSmith Integration - Evidence & Documentation

## Overview
This project integrates LangSmith for comprehensive LLM tracing and monitoring. LangSmith provides visibility into all LLM invocations, token usage, latency, and cost tracking.

## Current Status: ✅ ACTIVE

LangSmith tracing is now fully configured and operational. Traces are being successfully ingested into the LangSmith platform.

## Configuration

### Environment Setup
The project loads LangSmith configuration from `.env`:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=<your-langsmith-api-key>
LANGCHAIN_PROJECT=hari_loan_underwriting_chatbot_tracing
```

### Code Integration
- **Config Module**: `utils/langsmith_config.py` — Centralized LangSmith environment setup
- **LLM Service**: `services/llm_service.py` — Initializes ChatOpenAI clients with tracing enabled
- **Chain Wrapper**: `chains/underwriting_chain.py` — Uses `@traceable` decorator for explicit run tracking

## Evidence Screenshots

### LangSmith Dashboard - Active Traces
![LangSmith Tracing Dashboard](./langsmith_evidence_screenshot.png)
**What this shows:**
- Project: `loan-underwriting-ai`
- Multiple successful ChatOpenAI traces recorded
- Timestamps: 7/5/2026, 08:26, 08:23, 08:20, 08:16, 08:15+ (all successful)
- Input: Human messages from the chatbot UI
- Output: AI responses with proper latency tracking
- All traces marked with green checkmarks (successful completion)
- Latency metrics visible: 1.21s, 1.28s, 0.94s, 0.96s, 1.46s, 1.58s

## How Tracing Works

### Automatic Tracing
When `LANGCHAIN_TRACING_V2=true`, LangChain automatically traces:
1. LLM invocations (ChatOpenAI calls)
2. Token usage (input + output tokens)
3. Latency (response time)
4. Errors (if any)

### Explicit Tracing with @traceable
The `underwriting_chain` function is decorated with `@traceable(name="underwriting_chain")` to create a dedicated run for the entire underwriting workflow.

### Data Flow
```
User Input (Streamlit)
    ↓
/chat endpoint (FastAPI)
    ↓
underwriting_chain() [@traceable]
    ↓
ChatOpenAI.invoke() [auto-traced]
    ↓
LangSmith API
    ↓
LangSmith Dashboard
```

## Monitoring & Debugging

### View Traces in LangSmith
1. Go to https://smith.langchain.com
2. Select project: `hari_loan_underwriting_chatbot_tracing`
3. View all traces on the Tracing tab
4. Click any trace to drill down into details:
   - Input/output content
   - Token usage breakdown
   - Latency metrics
   - Cost estimates

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 403 Forbidden | Invalid API key or no workspace access | Regenerate API key in LangSmith, ensure workspace permissions |
| No traces appearing | LANGCHAIN_TRACING_V2 not set to true | Check `.env` and restart app |
| Wrong project name | Project name mismatch | Verify `LANGCHAIN_PROJECT` matches LangSmith project exactly |
| Traces delayed | Network latency or batch ingestion | Traces batch every 30s; wait and refresh |

## Costs & Metrics

LangSmith provides cost tracking:
- **Per-request cost**: Based on OpenAI token pricing
- **Monthly cost**: Aggregated across all traces
- **Dashboard**: Real-time cost visibility in the project dashboard

## Future Enhancements

- [ ] Custom evaluation logic within LangSmith
- [ ] Feedback loops for model fine-tuning
- [ ] Automated alerts for high-latency traces
- [ ] A/B testing framework for prompt variations

## References

- **LangSmith Docs**: https://docs.smith.langchain.com
- **LangChain Integration**: https://python.langchain.com/docs/langsmith
- **Project Config**: [.env](./.env)
- **Implementation Files**:
  - [utils/langsmith_config.py](../utils/langsmith_config.py)
  - [services/llm_service.py](../services/llm_service.py)
  - [chains/underwriting_chain.py](../chains/underwriting_chain.py)
