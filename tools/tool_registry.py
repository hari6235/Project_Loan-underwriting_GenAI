# FILE: tools/tool_registry.py
from tools.langchain_tools import (
    get_applicant_record,
    credit_score_analyzer,
    dti_calculator,
    document_verification,
    max_loan_by_credit_score,
    topup_eligibility,
    max_allowed_emi_for_target_dti,
    solve_tenure_for_target_emi,
    simulate_rate_comparison,
    knowledge_retrieval,
)

# Local (non-MCP) tools the agent may call. chains/base.py's all_tools()
# appends MCP-backed tools to this list to build the full catalogue passed
# to bind_tools(). This replaces the old hardcoded keyword cascade in
# tools/router.py (deleted -- no longer imported anywhere).
TOOLS = [
    get_applicant_record,
    credit_score_analyzer,
    dti_calculator,
    document_verification,
    max_loan_by_credit_score,
    topup_eligibility,
    max_allowed_emi_for_target_dti,
    solve_tenure_for_target_emi,
    simulate_rate_comparison,
    knowledge_retrieval,
]