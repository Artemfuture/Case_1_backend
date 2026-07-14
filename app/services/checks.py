import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from fastapi import UploadFile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.check import CheckDocumentRecord, CheckRecord
from app.schemas.check import (
    CheckDetailResponse,
    CheckListResponse,
    CheckStatus,
    DocumentSchema,
    DocumentType,
    ExtractedDataSchema,
    IssueLevel,
    IssueSchema,
    ProgramType,
)


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".jpg", ".png"}
STATUS_LABELS = {
    CheckStatus.approved: "Можно заявлять в банк",
    CheckStatus.rejected: "Нельзя заявлять в банк",
    CheckStatus.check_in_progress: "Проверка выполняется",
}
REQUIRED_DOCUMENTS = {
    ProgramType.federal: [DocumentType.contract, DocumentType.specification, DocumentType.invoice, DocumentType.act],
    ProgramType.regional: [DocumentType.contract, DocumentType.invoice, DocumentType.act],
}
DOCUMENT_LABELS = {
    DocumentType.contract: "договор",
    DocumentType.specification: "спецификация",
    DocumentType.invoice: "счёт",
    DocumentType.act: "акт/УПД",
}


@dataclass(slots=True)
class FileCheckResult:
    filename: str
    detected_type: DocumentType
    size_kb: float
    version: int
    file_path: Path


def _normalize_name(filename: str) -> str:
    return Path(filename).name.lower()


def detect_document_type(filename: str) -> DocumentType:
    normalized = re.sub(r"[._-]+", " ", _normalize_name(filename))

    patterns = (
        (DocumentType.contract, ("договор", "dogovor", "contract")),
        (DocumentType.specification, ("спецификац", "specification", "spec")),
        (DocumentType.invoice, ("счет", "счёт", "invoice", "bill")),
        (DocumentType.act, ("акт", "упд", "universal transfer document")),
    )

    for document_type, tokens in patterns:
        if any(token in normalized for token in tokens):
            return document_type

    return DocumentType.unknown


def validate_file_name(filename: str, size_bytes: int) -> list[IssueSchema]:
    issues: list[IssueSchema] = []
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        issues.append(
            IssueSchema(
                level=IssueLevel.error,
                message=f"Недопустимый формат файла: «{filename}». Разрешены PDF, DOCX, JPG, PNG.",
            )
        )

    if size_bytes > settings.max_file_size_bytes:
        issues.append(
            IssueSchema(
                level=IssueLevel.error,
                message=f"Файл «{filename}» превышает допустимый размер 20 МБ.",
            )
        )

    if detect_document_type(filename) is DocumentType.unknown:
        issues.append(IssueSchema(level=IssueLevel.warning, message=f"Не удалось определить тип документа: «{filename}»"))

    return issues


def validate_package_completeness(program: ProgramType, documents: Sequence[DocumentSchema]) -> list[IssueSchema]:
    issues: list[IssueSchema] = []
    detected_types = {document.detected_type for document in documents}

    for required_document in REQUIRED_DOCUMENTS[program]:
        if required_document not in detected_types:
            issues.append(
                IssueSchema(
                    level=IssueLevel.error,
                    message=f"Отсутствует обязательный документ: {DOCUMENT_LABELS[required_document]}",
                )
            )

    return issues


def determine_status(issues: Sequence[IssueSchema]) -> CheckStatus:
    return CheckStatus.rejected if any(issue.level == IssueLevel.error for issue in issues) else CheckStatus.approved


def build_reason(issues: Sequence[IssueSchema]) -> str | None:
    error = next((issue.message for issue in issues if issue.level == IssueLevel.error), None)
    return error


def build_extracted_data(documents: Sequence[DocumentSchema]) -> ExtractedDataSchema:
    return ExtractedDataSchema()


class CheckService:
    def __init__(self, session: AsyncSession, uploads_dir: Path | None = None) -> None:
        self.session = session
        self.uploads_dir = uploads_dir or settings.uploads_dir

    async def create_check(self, program: ProgramType, uploads: Sequence[UploadFile]) -> CheckDetailResponse:
        check = CheckRecord(
            program=program.value,
            status=CheckStatus.check_in_progress.value,
            status_label=STATUS_LABELS[CheckStatus.check_in_progress],
            reason=None,
            issues=[],
            extracted={},
            document_count=0,
            checked_at=datetime.now(timezone.utc),
        )
        self.session.add(check)
        await self.session.flush()

        check_dir = self.uploads_dir / check.id
        check_dir.mkdir(parents=True, exist_ok=True)

        issues: list[IssueSchema] = []
        documents: list[DocumentSchema] = []
        version_counters: dict[DocumentType, int] = defaultdict(int)

        for upload in uploads:
            filename = upload.filename or "untitled"
            content = await upload.read()
            size_bytes = len(content)
            file_issues = validate_file_name(filename, size_bytes)
            issues.extend(file_issues)

            detected_type = detect_document_type(filename)
            version_counters[detected_type] += 1
            version = version_counters[detected_type]

            stored_path = check_dir / f"{version:02d}_{Path(filename).name}"
            stored_path.write_bytes(content)

            document_record = CheckDocumentRecord(
                check=check,
                name=Path(filename).name,
                detected_type=detected_type.value,
                version=version,
                file_path=str(stored_path),
                size_kb=round(size_bytes / 1024, 2),
            )
            self.session.add(document_record)
            documents.append(
                DocumentSchema(
                    name=document_record.name,
                    detected_type=detected_type,
                    size_kb=document_record.size_kb,
                    version=version,
                )
            )

        issues.extend(validate_package_completeness(program, documents))
        status = determine_status(issues)
        reason = build_reason(issues)
        extracted = build_extracted_data(documents)

        check.status = status.value
        check.status_label = STATUS_LABELS[status]
        check.reason = reason
        check.issues = [issue.model_dump() for issue in issues]
        check.extracted = extracted.model_dump()
        check.document_count = len(documents)
        check.checked_at = datetime.now(timezone.utc)

        await self.session.commit()

        return self._serialize_check(check, documents)

    async def list_checks(self) -> list[CheckListResponse]:
        result = await self.session.execute(select(CheckRecord).order_by(desc(CheckRecord.checked_at)))
        checks = result.scalars().all()
        return [self._serialize_check_list(check) for check in checks]

    async def get_check(self, check_id: str) -> CheckDetailResponse | None:
        result = await self.session.execute(
            select(CheckRecord)
            .options(selectinload(CheckRecord.documents))
            .where(CheckRecord.id == check_id)
        )
        check = result.scalar_one_or_none()
        if check is None:
            return None
        documents = [
            DocumentSchema(
                name=document.name,
                detected_type=DocumentType(document.detected_type),
                size_kb=document.size_kb,
                version=document.version,
            )
            for document in check.documents
        ]
        return self._serialize_check(check, documents)

    def _serialize_check(
        self,
        check: CheckRecord,
        documents: list[DocumentSchema] | None = None,
    ) -> CheckDetailResponse:
        return CheckDetailResponse(
            check_id=check.id,
            program=ProgramType(check.program),
            status=CheckStatus(check.status),
            status_label=check.status_label,
            reason=check.reason,
            issues=[IssueSchema.model_validate(issue) for issue in check.issues],
            documents=documents or [],
            extracted=ExtractedDataSchema.model_validate(check.extracted),
            checked_at=check.checked_at,
            document_count=check.document_count,
        )

    def _serialize_check_list(self, check: CheckRecord) -> CheckListResponse:
        return CheckListResponse(
            id=check.id,
            checked_at=check.checked_at,
            program=ProgramType(check.program),
            status=CheckStatus(check.status),
            document_count=check.document_count,
        )