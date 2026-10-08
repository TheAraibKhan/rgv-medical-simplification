from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    status: str
    mode: str
    llm_provider: str
    verifier_provider: str
