from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.check import CheckDetailResponse, CheckListResponse, ProgramType
from app.services.checks import CheckService


router = APIRouter(prefix="/checks", tags=["checks"])


@router.post("", response_model=CheckDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_check(
    program: Annotated[ProgramType, Form(...)],
    files: Annotated[list[UploadFile], File(...)],
    session: AsyncSession = Depends(get_db),
) -> CheckDetailResponse:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Необходимо передать хотя бы один файл")

    service = CheckService(session)
    return await service.create_check(program=program, uploads=files)


@router.get("", response_model=list[CheckListResponse])
async def list_checks(session: AsyncSession = Depends(get_db)) -> list[CheckListResponse]:
    service = CheckService(session)
    return await service.list_checks()


@router.get("/{check_id}", response_model=CheckDetailResponse)
async def get_check(check_id: str, session: AsyncSession = Depends(get_db)) -> CheckDetailResponse:
    service = CheckService(session)
    check = await service.get_check(check_id)
    if check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проверка не найдена")
    return check