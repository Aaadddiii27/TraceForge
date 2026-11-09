"""
Tool registry API endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import ToolListResponse, ToolResponse
from app.services.tool_service import ToolNotFoundError, ToolService

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get(
    "",
    response_model=ToolListResponse,
    summary="List all registered tools",
)
async def list_tools(db: AsyncSession = Depends(get_db)) -> ToolListResponse:
    service = ToolService(db)
    tools = await service.list_tools()
    return ToolListResponse(
        items=[ToolResponse.model_validate(t) for t in tools],
        total=len(tools),
    )


@router.get(
    "/{tool_name}",
    response_model=ToolResponse,
    summary="Get tool detail by name",
)
async def get_tool(tool_name: str, db: AsyncSession = Depends(get_db)) -> ToolResponse:
    service = ToolService(db)
    try:
        tool = await service.get_by_name(tool_name)
    except ToolNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Tool '{tool_name}' not found"},
        )
    return ToolResponse.model_validate(tool)
