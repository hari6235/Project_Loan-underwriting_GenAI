from pydantic import BaseModel


class RiskAssessment(BaseModel):
    category: str
    risk_score: int
    risk_category: str
    approval_probability: str
    recommendation: str