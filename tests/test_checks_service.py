from app.schemas.check import CheckStatus, DocumentType, IssueLevel, IssueSchema, ProgramType
from app.services.checks import detect_document_type, determine_status, validate_package_completeness


def test_detect_contract_document_type() -> None:
    assert detect_document_type("dogovor_47.pdf") == DocumentType.contract


def test_detect_specification_document_type() -> None:
    assert detect_document_type("specification_v2.docx") == DocumentType.specification


def test_detect_invoice_document_type_with_cyrillic_name() -> None:
    assert detect_document_type("счёт_10.jpg") == DocumentType.invoice


def test_regional_package_without_specification_is_approved() -> None:
    documents = [
        type("Doc", (), {"detected_type": DocumentType.contract}),
        type("Doc", (), {"detected_type": DocumentType.invoice}),
        type("Doc", (), {"detected_type": DocumentType.act}),
    ]

    issues = validate_package_completeness(ProgramType.regional, documents)

    assert issues == []
    assert determine_status(issues) == CheckStatus.approved


def test_federal_package_missing_specification_is_rejected() -> None:
    documents = [
        type("Doc", (), {"detected_type": DocumentType.contract}),
        type("Doc", (), {"detected_type": DocumentType.invoice}),
        type("Doc", (), {"detected_type": DocumentType.act}),
    ]

    issues = validate_package_completeness(ProgramType.federal, documents)

    assert any(issue.level == IssueLevel.error for issue in issues)
    assert determine_status(issues) == CheckStatus.rejected


def test_warning_only_issue_keeps_approved_status() -> None:
    issues = [IssueSchema(level=IssueLevel.warning, message="Не удалось определить тип документа")]

    assert determine_status(issues) == CheckStatus.approved