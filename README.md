# Loan Underwriting & Credit Risk Assistant

A LangChain-powered AI assistant for banking operations. This project helps with loan underwriting, credit risk assessment, and KYC document verification using a conversational AI interface.

---

## 🎯 Features

- **Multi-turn Conversations** - Maintains context across 10 conversation turns
- **Loan Risk Assessment** - Analyzes credit scores and applicant risk profiles
- **DTI Calculation** - Computes debt-to-income ratios for loan eligibility
- **Document Verification** - Validates KYC documents (PAN, Aadhaar, etc.)
- **Security First** - PII detection and prompt injection prevention built-in
- **Easy to Use** - Streamlit frontend with intuitive chat interface
- **Production Ready** - FastAPI backend with proper error handling

---

## 📁 Project Structure

```
.
├── api/                          # FastAPI backend
│   ├── main.py                   # FastAPI app setup & endpoints
│   └── routes.py                 # Chat & reset routes
├── app.py                        # Streamlit frontend
├── chains/                       # LangChain workflows
│   └── underwriting_chain.py     # Loan underwriting chain
├── core/                         # Core utilities
│   └── chain.py                  # Chain orchestration
├── guardrails/                   # Input validation & security
│   ├── pii_detector.py           # Detects PII (Aadhaar, PAN, Phone)
│   ├── prompt_injection.py       # Blocks injection attempts
│   └── topic_filter.py           # Ensures banking-related queries
├── memory/                       # Conversation memory
│   └── memory_store.py           # SQLite-based conversation storage
├── models/                       # Data validation schemas
│   ├── response_model.py         # Pydantic response models
│   └── risk_model.py             # Risk assessment models
├── prompts/                      # LLM prompts & examples
│   ├── templates.py              # Prompt templates
│   ├── few_shots.yaml            # Few-shot examples
│   ├── system_prompt.yaml        # System instructions
│   └── underwriting_prompt.yaml  # Underwriting-specific prompts
├── services/                     # Business logic
│   └── llm_service.py            # LLM calls & tool routing
├── tools/                        # Domain-specific tools
│   ├── credit_score_tool.py      # Credit analysis tool
│   ├── dti_tool.py               # DTI ratio calculator
│   ├── document_tool.py          # Document verification
│   ├── langchain_tools.py        # LangChain tool wrappers
│   ├── router.py                 # Tool routing logic
│   └── tool_registry.py          # Tool registry
├── vectorstore/                  # Vector search & embeddings
│   └── example_store.py          # FAISS vector store
├── logs/                         # Application logs
│   └── interactions.log          # Interaction logs
├── memory.db                     # SQLite conversation database
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables
└── .gitignore                    # Git ignore rules
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/hari6235/Project_Loan-underwriting_GenAI.git
cd Project_Loan-underwriting_GenAI
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment**
```bash
cp .env.example .env  # if available, or create manually
echo "OPENAI_API_KEY=your-api-key-here" >> .env
```

5. **Run the application**

Open two terminal windows:

**Terminal 1 - Backend API**
```bash
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 - Frontend UI**
```bash
streamlit run app.py
```

The Streamlit app will open at `http://localhost:8501`

---

## 📡 API Endpoints

### POST /chat
Process a user message and get an AI response.

**Request:**
```json
{
  "session_id": "user1",
  "message": "What is the credit score for applicant A-9912?"
}
```

**Response:**
```json
{
  "response": {
    "type": "tool_response",
    "response": {
      "credit_score": 720,
      "category": "GOOD",
      "risk_level": "MEDIUM",
      "approval_probability": "80%"
    }
  },
  "session_id": "user1",
  "history": [...]
}
```

### POST /reset
Clear conversation memory for a session.

**Request:**
```bash
curl -X POST "http://localhost:8000/reset?session_id=user1"
```

**Response:**
```json
{
  "message": "memory cleared",
  "session_id": "user1"
}
```

### GET /health
Check API health status.

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "loan-underwriting-ai"
}
```

---

## 🛠️ Core Tools

### 1. Credit Score Analyzer
Evaluates credit score and determines risk classification.

```python
from tools.credit_score_tool import credit_score_analyzer

result = credit_score_analyzer(720)
# Output: {credit_score: 720, category: "GOOD", risk_level: "MEDIUM", ...}
```

**Risk Classifications:**
- **750+**: EXCELLENT (Low Risk)
- **700-749**: GOOD (Medium Risk)
- **650-699**: MODERATE (High Risk)
- **Below 650**: POOR (Reject)

### 2. DTI Calculator
Calculates debt-to-income ratio for loan eligibility.

```python
from tools.dti_tool import dti_calculator

result = dti_calculator(monthly_income=100000, emi=30000)
# Output: {dti_ratio: 0.30, risk_level: "LOW", max_loan_multiplier: 5}
```

**Risk Levels:**
- **≤0.3**: LOW (Max loan = 5x income)
- **0.3-0.5**: MEDIUM (Max loan = 3x income)
- **>0.5**: HIGH (Max loan = 1.5x income)

### 3. Document Verification
Validates KYC documents for compliance.

```python
from tools.document_tool import document_verification

result = document_verification(pan="ABCDE1234F", aadhaar="123456789012")
# Output: {pan_valid: true, aadhaar_valid: true, status: "VERIFIED", ...}
```

**Supported Documents:**
- PAN (10 characters)
- Aadhaar (12 digits)
- ITR documents

---

## 🔒 Security Features

### PII Detection
Blocks personally identifiable information:
- Aadhaar numbers (12 digits)
- PAN numbers (10-char format)
- Phone numbers (10 digits)

### Prompt Injection Detection
Prevents malicious prompt modification:
- Blocks common injection keywords
- Validates input before processing

### Topic Filtering
Ensures queries are banking-related:
- Validates against banking keywords
- Rejects off-topic questions

---

## 💾 Memory Management

Conversations are stored in SQLite for persistence:
- **Database**: `memory.db`
- **Storage**: Up to 10 conversation turns per session
- **Methods**:
  - `add(session_id, user_msg, assistant_msg)` - Store interaction
  - `get(session_id)` - Retrieve conversation history
  - `clear(session_id)` - Clear session memory

---

## 📝 Example Queries

### Banking FAQs
- "What documents are required for KYC?"
- "Can I open a savings account online?"
- "How is loan interest calculated?"

### Loan Analysis
- "What is the credit score for applicant A-9912?"
- "Calculate DTI for income 12L and liabilities 4.8L"
- "Verify KYC documents for loan #7745"

### Risk Assessment
- "Why was application #3310 flagged as high risk?"
- "What is the maximum loan amount for a 680 credit score?"
- "Re-assess applicant with new co-applicant income"

---

## 📊 Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI + Python |
| **Frontend** | Streamlit |
| **LLM** | OpenAI GPT-4o-mini |
| **Vector DB** | FAISS (ChromaDB) |
| **Memory** | SQLite |
| **Validation** | Pydantic |
| **Prompt Framework** | LangChain |
| **Async** | Python asyncio |

---

## 📋 Dependencies

Key packages:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `streamlit` - UI framework
- `langchain` - LLM orchestration
- `langchain-openai` - OpenAI integration
- `pydantic` - Data validation
- `faiss-cpu` - Vector storage
- `tenacity` - Retry logic
- `langsmith` - LLM tracing

See `requirements.txt` for complete list.

---

## 🧪 Testing

Test queries covering different scenarios:

1. Simple FAQs
2. Tool invocation (credit score, DTI)
3. Document verification
4. Multi-turn conversations
5. Edge cases & error handling

---

## 🐛 Troubleshooting

### API Connection Error
- Ensure FastAPI is running: `uvicorn api.main:app --reload`
- Check port 8000 is available
- Verify `.env` has valid `OPENAI_API_KEY`

### Memory Issues
- Check `memory.db` exists in project root
- Clear old sessions: Call `/reset` endpoint
- Restart app if database is corrupted

### Tool Not Responding
- Verify tool imports in `services/llm_service.py`
- Check tool parameters match function signatures
- Review logs in `logs/interactions.log`

### Slow Responses
- Check OpenAI API rate limits
- Verify network connectivity
- Consider adding response caching (in progress)

---
## 🚧 Roadmap

Planned improvements:
- [ ] Add retry logic with exponential backoff
- [ ] Integrate LangSmith for tracing
- [ ] Add in-memory caching layer
- [ ] Redis support for distributed sessions
- [ ] Enhanced error handling
- [ ] Comprehensive logging
- [ ] API rate limiting
- [ ] User authentication

---

## 📄 License

This project is for educational and demonstration purposes.

---

## 👤 Author

Harisankar has Created this project as a demonstration of LangChain-based banking AI assistant and is submitted for evaluation to the Trainer from Learquest(Surya).

---

## 📞 Support

For issues or questions:
1. Check logs: `cat logs/interactions.log`
2. Review API docs: `http://localhost:8000/docs`
3. Test endpoints manually in Streamlit UI
4. Verify `.env` configuration
