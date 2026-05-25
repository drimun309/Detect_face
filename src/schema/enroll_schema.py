"""Schemas for face enrollment API."""

from pydantic import BaseModel, Field


class EnrolledPersonSchema(BaseModel):
    name: str
    count: int


class EnrolledListSchema(BaseModel):
    items: list[EnrolledPersonSchema]
    total_embeddings: int


class EnrollResultSchema(BaseModel):
    saved: int
    photos_ok: int
    photos_skip: int
    frames_ok: int
    frames_skip: int
    logs: list[str]
