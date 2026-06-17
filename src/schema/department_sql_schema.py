"""SQLModel table for departments (PostgreSQL)."""

from typing import Optional

from sqlmodel import Field, SQLModel


class DepartmentSqlSchema(SQLModel, table=True):
    __tablename__ = "departments"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=128, unique=True)
