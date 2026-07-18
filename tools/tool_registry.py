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
    evaluate_loan_request,
    flag_policy_override,
    knowledge_retrieval,
)

# Local (non-MCP) tools the agent may call. chains/base.py's all_tools()
# appends MCP-backed tools to this list to build the full catalogue passed
# to bind_tools(). This replaces the old hardcoded keyword cascade in
# tools/router.py (deleted -- no longer imported anywhere).
#
# evaluate_loan_request and flag_policy_override exist specifically so
# the HITL trigger engine (hitl/triggers.py, config/hitl_rules.yaml) has
# real structured data to evaluate -- without them, "loan_amount" and
# "policy_override_requested" never appear anywhere in decision_context,
# no matter what the agent says in prose.
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
    evaluate_loan_request,
    flag_policy_override,
    knowledge_retrieval,
]