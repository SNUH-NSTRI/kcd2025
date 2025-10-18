"""Study management schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class CreateStudyRequest(BaseModel):
    """Request to create a new study."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Study name (e.g., trial brief title)")
    nct_id: str = Field(..., pattern=r"^NCT\d{8}$", description="NCT ID (e.g., NCT03389555)", alias="nctId")
    research_question: str = Field(..., description="Research question to investigate", alias="researchQuestion")
    medicine_family: str = Field(..., description="Medicine family for treatment analysis", alias="medicineFamily")
    medicine_generic: str | None = Field(None, description="Generic medicine name", alias="medicineGeneric")
    medicine_brand: str | None = Field(None, description="Brand medicine name", alias="medicineBrand")


class StudyResponse(BaseModel):
    """Response after creating a study."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=lambda x: ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(x.split('_'))))

    status: str
    message: str
    study_id: str = Field(..., alias="studyId")


class StudyProgressStep(BaseModel):
    """Progress information for a single step."""

    model_config = ConfigDict(populate_by_name=True)

    step: str
    label: str
    status: str  # "pending" | "in_progress" | "done" | "failed"
    started_at: str | None = Field(None, alias="startedAt")
    completed_at: str | None = Field(None, alias="completedAt")
    error: str | None = None


class StudyStatus(BaseModel):
    """Current status of study processing."""

    model_config = ConfigDict(populate_by_name=True)

    study_id: str = Field(..., alias="studyId")
    overall_status: str = Field(..., alias="overallStatus")  # "created" | "processing" | "completed" | "failed"
    current_step: str | None = Field(None, alias="currentStep")
    steps: list[StudyProgressStep]
    created_at: str = Field(..., alias="createdAt")
    updated_at: str = Field(..., alias="updatedAt")
    error: str | None = None


class StudyMetadata(BaseModel):
    """Study metadata stored in workspace."""

    study_id: str
    name: str
    nct_id: str
    research_question: str
    medicine_family: str
    medicine_generic: str | None = None
    medicine_brand: str | None = None
    created_at: str
    updated_at: str
