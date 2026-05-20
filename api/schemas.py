"""
Pydantic request and response schemas for the AgentX FastAPI service.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

CLAIM_SAFETY_NOTE = (
    "This local API boundary runs AgentX validation workflows for development "
    "and portfolio evidence. It is not a production regulatory approval system."
)


class HealthResponse(BaseModel):
    status: str
    system: str
    version: str
    metrics_available: bool
    evidence_available: bool


class MetricsResponse(BaseModel):
    roc_auc: float
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    dataset_rows: int
    feature_count: int
    model_type: str
    evidence_source: str


class ValidationRunRequest(BaseModel):
    run_compliance_agent: bool = Field(
        default=False,
        description="Call the Groq LLM compliance agent. Requires GROQ_API_KEY; "
                    "uses cached fallback when the key is absent.",
    )
    run_drift_monitor: bool = Field(
        default=True,
        description="Run the KS-test drift monitor against the reference dataset.",
    )
    regenerate_reports: bool = Field(
        default=True,
        description="Write the Markdown validation report after the pipeline run.",
    )


class ArtifactStatus(BaseModel):
    path: str
    exists: bool
    size_bytes: Optional[int] = None


class ValidationRunResponse(BaseModel):
    status: str
    message: str
    metrics: Dict
    artifacts: List[str]
    warnings: List[str]
    evidence_note: str = CLAIM_SAFETY_NOTE


class EvidenceFileInfo(BaseModel):
    name: str
    size_bytes: int


class EvidenceResponse(BaseModel):
    evidence_files: List[EvidenceFileInfo]
    generated_artifacts: List[ArtifactStatus]
    governance_available: bool = False
    mlflow_tracking_available: bool = False
    claim_safety_note: str = CLAIM_SAFETY_NOTE


class GovernanceRunHistoryItem(BaseModel):
    validation_run_id: Optional[str] = None
    created_at_utc: Optional[str] = None
    run_type: Optional[str] = None
    reviewer_status: Optional[str] = None
    risk_flags: List[str] = []
    roc_auc: Optional[float] = None
    drift_detected: Optional[bool] = None
    file: Optional[str] = None


class GovernanceLatestResponse(BaseModel):
    available: bool
    validation_run_id: Optional[str] = None
    created_at_utc: Optional[str] = None
    system_name: Optional[str] = None
    system_version: Optional[str] = None
    run_type: Optional[str] = None
    roc_auc: Optional[float] = None
    drift_detected: Optional[bool] = None
    drifted_features: List[str] = []
    compliance_status: Optional[str] = None
    reviewer_status: Optional[str] = None
    risk_flags: List[str] = []
    artifacts_present: int = 0
    artifacts_total: int = 0
    claim_safety_note: str = CLAIM_SAFETY_NOTE


class GovernanceHistoryResponse(BaseModel):
    available: bool
    count: int
    runs: List[GovernanceRunHistoryItem]
    claim_safety_note: str = CLAIM_SAFETY_NOTE
