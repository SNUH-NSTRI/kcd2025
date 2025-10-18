"""Pydantic schemas for workspace endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkspaceDataResponse(BaseModel):
    """Response schema for workspace data."""

    project_id: str = Field(..., description="Project identifier")
    stage: str = Field(..., description="Pipeline stage")
    files: dict[str, Any] = Field(..., description="Available files and their metadata")
    data: dict[str, Any] | None = Field(None, description="File contents if requested")


class ProjectInfo(BaseModel):
    """Project information schema."""

    project_id: str = Field(..., description="Project identifier")
    stages: list[str] = Field(..., description="Available pipeline stages")
    created_at: str | None = Field(None, description="Creation timestamp")


class ProjectListResponse(BaseModel):
    """Response schema for project list."""

    projects: list[ProjectInfo] = Field(..., description="List of projects")
    total: int = Field(..., description="Total project count")

