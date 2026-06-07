# Loan Underwriting & Credit Risk Assistant

## Project Overview

The Loan Underwriting & Credit Risk Assistant is a Generative AI-powered banking application that assists users with:

* Banking FAQs
* Loan eligibility and EMI calculations
* KYC document requirements
* Credit risk assessment
* Loan underwriting decision support

The project demonstrates Prompt Engineering, Few-Shot Learning, Structured JSON Responses, Pydantic Validation, Input Guardrails, Explainable Risk Assessment, and a Streamlit-based User Interface.

---

## Features

### Banking FAQ Chatbot

* Handles account, KYC, loan, and insurance queries
* Generates structured JSON responses
* Validates responses using Pydantic

### Loan Underwriting & Credit Risk Assessment

* Calculates Debt-to-Income (DTI) Ratio
* Generates Risk Score and Risk Category
* Provides underwriting recommendations
* Supports explainable step-by-step reasoning

### Input Guardrails

* PII Detection
* Prompt Injection Defense
* Off-Topic Query Filtering

### Prompt Engineering & Few-Shot Learning

* Role-based system prompts
* Few-shot examples for banking intents
* Structured response instructions
* JSON-only output enforcement

### User Interface

* Streamlit-based application
* Interactive banking chatbot
* Loan underwriting dashboard
* Underwriting reasoning viewer

---

## Repository Structure

```text
Project_1_Loan_Underwriting_Credit_Risk_Assistant/

├── guardrails/
│   ├── pii_detector.py
│   ├── topic_filter.py
│   └── prompt_injection.py

├── models/
|   ├── _init_.py
│   ├── response_model.py
│   └── risk_model.py

├── prompts/
│   ├── few_shots.yaml
|   ├── system_prompt.yaml
│   └── underwriting_prompt.yaml

├── reports/
│   └── evaluation_report.md

├── services/
|   ├── _init_.py
│   └── llm_service.py

├── .env
├── app.py
├── README.md
├── requirements.txt
├── .gitignore


```

---

## Setup Instructions (Ubuntu Linux)

### 1. Clone Repository

```bash
git clone <repository_url>
cd Project_1_Loan_Underwriting_Credit_Risk_Assistant
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file and add:

```text
OPENAI_API_KEY=your_openai_api_key_here
```

### 5. Run Application

```bash
streamlit run app.py
```

Application URL:

```text
http://localhost:8501
```

---

## Example Banking Queries

* What documents are required for KYC?
* Can I open a savings account online?
* What is a home loan EMI?
* How is loan interest calculated?
* What is term insurance?

---

## Example Underwriting Inputs

### Low Risk Applicant

```text
Monthly Income: 150000
Existing EMI: 10000
Credit Score: 790
Loan Amount: 2500000
```

### Medium Risk Applicant

```text
Monthly Income: 80000
Existing EMI: 25000
Credit Score: 710
Loan Amount: 2000000
```

### High Risk Applicant

```text
Monthly Income: 40000
Existing EMI: 25000
Credit Score: 620
Loan Amount: 3000000
```

---

## Evaluation

The project was evaluated using:

* Banking FAQ Functional Testing
* Intent Classification Validation
* PII Detection Testing
* Prompt Injection Testing
* Off-Topic Query Testing
* JSON Schema Validation
* Loan Underwriting Assessment Testing

Detailed results are available in:

```text
reports/evaluation_report.md
```

---

## Technologies Used

* Python 3.11.13
* Streamlit
* OpenAI API
* Pydantic
* PyYAML
* Python Dotenv

---

## Key Concepts Demonstrated

* Prompt Engineering
* Few-Shot Learning
* Structured JSON Outputs
* Pydantic Validation
* Input Guardrails
* Explainable Risk Assessment
* Banking Domain AI Assistant

---

## License

This project is intended for learning and demonstration purposes.
