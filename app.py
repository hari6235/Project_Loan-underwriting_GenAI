import streamlit as st
import json

from guardrails.pii_detector import contains_pii
from guardrails.topic_filter import is_banking_query
from guardrails.prompt_injection import detect_prompt_injection

from services.llm_service import ask_llm

from models.response_model import BankingResponse
from models.risk_model import RiskAssessment


st.set_page_config(
    page_title="Loan Underwriting & Credit Risk Assistant",
    layout="wide"
)

st.title("🏦 Loan Underwriting & Credit Risk Assistant")

# ==========================================================
# BANKING FAQ CHATBOT
# ==========================================================

st.header("💬 Banking FAQ Chatbot")

query = st.text_area(
    "Ask a banking question"
)

if st.button("Submit Question"):

    if contains_pii(query):

        st.error(
            "PII Detected. Please remove personal information."
        )

    elif detect_prompt_injection(query):

        st.error(
            "Prompt Injection Attempt Detected."
        )

    elif not is_banking_query(query):

        st.error(
            "I am a Banking and Loan Underwriting Assistant designed to help with banking, loans, credit risk assessment, KYC requirements, account services, interest rates, and related financial queries. Please ask a banking or financial services question to continue."
        )

    else:

        response = ask_llm(query)

        try:

            parsed = BankingResponse(
                **json.loads(response)
            )

            st.success(
                "Validated Response"
            )

            st.json(
                parsed.model_dump()
            )

        except Exception as e:

            st.error(
                f"Validation Failed: {e}"
            )

            st.text(response)

# ==========================================================
# LOAN UNDERWRITING SECTION
# ==========================================================

st.divider()

st.header("📊 Loan Underwriting Assessment")

salary = st.number_input(
    "Monthly Income",
    min_value=0,
    value=0
)

emi = st.number_input(
    "Existing EMI",
    min_value=0,
    value=0
)

credit_score = st.number_input(
    "Credit Score",
    min_value=300,
    max_value=900,
    value=750
)

loan_amount = st.number_input(
    "Loan Amount",
    min_value=0,
    value=0
)

if st.button("Assess Risk"):

    if salary == 0 or loan_amount == 0:

        st.error(
            "Salary and Loan Amount must be greater than 0."
        )

    else:

        # --------------------------------------------------
        # Debt-to-Income Ratio
        # --------------------------------------------------

        dti = emi / salary

        # --------------------------------------------------
        # Credit Score Evaluation
        # --------------------------------------------------

        if credit_score > 750:

            credit_category = "Excellent"

        elif 700 <= credit_score <= 750:

            credit_category = "Good"

        elif 650 <= credit_score < 700:

            credit_category = "Moderate"

        else:

            credit_category = "High Risk"

        # --------------------------------------------------
        # Risk Scoring
        # --------------------------------------------------

        risk_score = 50

        if credit_category == "Excellent":

            risk_score -= 20

        elif credit_category == "Good":

            risk_score -= 10

        elif credit_category == "Moderate":

            risk_score += 10

        else:

            risk_score += 20

        if dti > 0.50:

            risk_score += 30

        elif dti > 0.40:

            risk_score += 10

        else:

            risk_score -= 5

        risk_score = max(
            0,
            min(100, int(risk_score))
        )

        # --------------------------------------------------
        # Risk Category
        # --------------------------------------------------

        if risk_score < 30:

            risk_category = "LOW"

            recommendation = "APPROVE"

        elif risk_score < 60:

            risk_category = "MEDIUM"

            recommendation = "CONSIDER"

        else:

            risk_category = "HIGH"

            recommendation = "REJECT"

        approval_probability = f"{100 - risk_score}%"

        assessment = RiskAssessment(

            category="loan_underwriting",

            risk_score=risk_score,

            risk_category=risk_category,

            approval_probability=approval_probability,

            recommendation=recommendation
        )

        # --------------------------------------------------
        # Dashboard Metrics
        # --------------------------------------------------

        st.success(
            "Risk Assessment Completed Successfully"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Risk Score",
                risk_score
            )

        with col2:
            st.metric(
                "Credit Score",
                credit_score
            )

        with col3:
            st.metric(
                "DTI Ratio",
                round(dti, 2)
            )

        st.subheader("Assessment Result")

        st.json(
            assessment.model_dump()
        )

        # --------------------------------------------------
        # Explainability Section
        # --------------------------------------------------

        with st.expander(
            "View Underwriting Reasoning"
        ):

            st.write(
                f"Step 1: Monthly Income Evaluated = ₹{salary:,.0f}"
            )

            st.write(
                f"Step 2: Existing EMI Evaluated = ₹{emi:,.0f}"
            )

            st.write(
                f"Step 3: Debt-to-Income Ratio Calculated = {round(dti, 2)}"
            )

            st.write(
                f"Step 4: Credit Score Evaluated = {credit_score}"
            )

            st.write(
                f"Step 5: Credit Category = {credit_category}"
            )

            st.write(
                f"Step 6: Risk Score Generated = {risk_score}"
            )

            st.write(
                f"Step 7: Risk Category Determined = {risk_category}"
            )

            st.write(
                f"Step 8: Final Recommendation = {recommendation}"
            )