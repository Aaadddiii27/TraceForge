"""
Tool Service — CRUD for tool registry records and upsert on startup.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ToolRecord
from app.tools.base import registry


class ToolNotFoundError(Exception):
    pass


class ToolService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync_registry_to_db(self) -> None:
        """
        Upsert all registered in-memory tools into the tools table.
        Called at application startup.
        """
        for tool in registry.list_tools():
            record_dict = tool.to_record_dict()
            stmt = select(ToolRecord).where(ToolRecord.name == tool.name)
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.description = record_dict["description"]
                existing.version = record_dict["version"]
                existing.input_schema = record_dict["input_schema"]
                existing.output_schema = record_dict["output_schema"]
                existing.permission_level = record_dict["permission_level"]
                existing.timeout_seconds = record_dict["timeout_seconds"]
            else:
                self.db.add(ToolRecord(**record_dict))
        await self.db.commit()

    async def list_tools(self) -> list[ToolRecord]:
        result = await self.db.execute(select(ToolRecord).order_by(ToolRecord.name))
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> ToolRecord:
        result = await self.db.execute(select(ToolRecord).where(ToolRecord.name == name))
        tool = result.scalar_one_or_none()
        if tool is None:
            raise ToolNotFoundError(f"Tool '{name}' not found")
        return tool
