from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class EnvironmentState(BaseModel):
    soil: Dict[str, Any] = Field(default_factory=dict)
    climate: Dict[str, Any] = Field(default_factory=dict)
    land: Dict[str, Any] = Field(default_factory=dict)
    biodiversity: Dict[str, Any] = Field(default_factory=dict)
    human_impact: Dict[str, Any] = Field(default_factory=dict)
    location: Optional[str] = None

class AnalyzeRequest(BaseModel):
    session_id: str = "default"
    message: Optional[str] = None
    environment: Optional[EnvironmentState] = None
    top_k: int = 5

class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str
    top_k: int = 5
