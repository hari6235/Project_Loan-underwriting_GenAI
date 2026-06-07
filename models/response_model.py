from pydantic import BaseModel


class BankingResponse(BaseModel):

    category: str
    answer: str
    confidence_score: float
    recommendation: str