from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ProgramType(str, Enum):
    federal = "federal"
    regional = "regional"


class CheckStatus(str, Enum):
    approved = "approved"
    rejected = "rejected"
    check_in_progress = "check_in_progress"


class IssueLevel(str, Enum):
    error = "error"
    warning = "warning"


class DocumentType(str, Enum):
    contract = "contract"
    specification = "specification"
    invoice = "invoice"
    act = "act"
    unknown = "unknown"


class IssueSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    level: IssueLevel
    message: str


class DocumentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    detected_type: DocumentType
    size_kb: float
    version: int


class ExtractedDataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    contractor: str | None = None
    amount: str | None = None
    date: str | None = None
    subject: str | None = None


class CheckDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    check_id: str
    program: ProgramType
    status: CheckStatus
    status_label: str
    reason: str | None = None
    issues: list[IssueSchema]
    documents: list[DocumentSchema]
    extracted: ExtractedDataSchema
    checked_at: datetime
    document_count: int


class CheckListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    checked_at: datetime
    program: ProgramType
    status: CheckStatus
    document_count: int
