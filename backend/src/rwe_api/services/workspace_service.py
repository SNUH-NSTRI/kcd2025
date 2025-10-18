"""Service for workspace operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class WorkspaceService:
    """Service for accessing workspace data."""

    def __init__(self, workspace_root: Path):
        """Initialize workspace service.

        Args:
            workspace_root: Root directory for workspace
        """
        self.workspace_root = workspace_root

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects in workspace."""
        if not self.workspace_root.exists():
            return []

        projects = []
        for project_dir in self.workspace_root.iterdir():
            if project_dir.is_dir():
                stages = [
                    stage.name
                    for stage in project_dir.iterdir()
                    if stage.is_dir()
                ]
                projects.append({
                    "project_id": project_dir.name,
                    "stages": sorted(stages),
                })

        return projects

    def get_project_stage_data(
        self, project_id: str, stage: str
    ) -> dict[str, Any]:
        """Get data for a specific project stage.

        Args:
            project_id: Project identifier
            stage: Pipeline stage name

        Returns:
            Dictionary containing stage data
        """
        stage_dir = self.workspace_root / project_id / stage

        if not stage_dir.exists():
            raise FileNotFoundError(f"Stage directory not found: {stage_dir}")

        # List all files in stage directory
        files = {}
        for file_path in stage_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(stage_dir)
                files[str(rel_path)] = {
                    "size": file_path.stat().st_size,
                    "extension": file_path.suffix,
                }

        return {
            "project_id": project_id,
            "stage": stage,
            "files": files,
        }

    def read_file(
        self, project_id: str, stage: str, filename: str
    ) -> dict[str, Any]:
        """Read a specific file from workspace.

        Args:
            project_id: Project identifier
            stage: Pipeline stage name
            filename: Name of file to read

        Returns:
            Dictionary containing file content
        """
        file_path = self.workspace_root / project_id / stage / filename

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Handle different file types
        if file_path.suffix == ".json":
            with file_path.open("r", encoding="utf-8") as f:
                content = json.load(f)
        elif file_path.suffix == ".jsonl":
            with file_path.open("r", encoding="utf-8") as f:
                content = [json.loads(line) for line in f]
        elif file_path.suffix in {".txt", ".md", ".sql"}:
            with file_path.open("r", encoding="utf-8") as f:
                content = f.read()
        elif file_path.suffix == ".parquet":
            # For parquet, return metadata only (would need pyarrow to read)
            content = {"type": "parquet", "size": file_path.stat().st_size}
        else:
            # For other files, return metadata
            content = {
                "type": "binary",
                "size": file_path.stat().st_size,
                "extension": file_path.suffix,
            }

        return {
            "filename": filename,
            "content": content,
        }

    def get_corpus(self, project_id: str) -> dict[str, Any]:
        """Get literature corpus for a project."""
        return self.read_file(project_id, "lit", "corpus.jsonl")

    def get_schema(self, project_id: str) -> dict[str, Any]:
        """Get trial schema for a project."""
        return self.read_file(project_id, "schema", "trial_schema.json")

    def get_filter_spec(self, project_id: str) -> dict[str, Any]:
        """Get filter specification for a project."""
        return self.read_file(project_id, "filters", "filter_spec.json")

    def get_cohort(self, project_id: str) -> dict[str, Any]:
        """Get cohort data for a project."""
        return self.read_file(project_id, "cohort", "cohort.json")

    def get_cohort_summary(self, project_id: str) -> dict[str, Any]:
        """Get cohort summary for a project."""
        return self.read_file(project_id, "cohort", "summary.json")

    def get_analysis(self, project_id: str) -> dict[str, Any]:
        """Get analysis results for a project."""
        outcomes = self.read_file(project_id, "analysis", "outcomes.json")
        metrics = self.read_file(project_id, "analysis", "metrics.json")
        return {
            "outcomes": outcomes["content"],
            "metrics": metrics["content"],
        }

    def get_report(self, project_id: str) -> dict[str, Any]:
        """Get report for a project."""
        return self.read_file(project_id, "report", "report.md")

