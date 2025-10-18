from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import logging


@dataclass(frozen=True)
class PipelineContext:
    """Execution context shared across pipeline modules."""

    project_id: str
    workspace: Path
    config: Mapping[str, Any]
    hil_enabled: bool = False
    logger: logging.Logger | None = None


def create_context(
    project_id: str,
    workspace: Path,
    config: Mapping[str, Any],
    hil_enabled: bool = False,
    logger: logging.Logger | None = None,
) -> PipelineContext:
    """
    Helper for building a `PipelineContext` ensuring workspace directories exist.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    return PipelineContext(
        project_id=project_id,
        workspace=workspace,
        config=config,
        hil_enabled=hil_enabled,
        logger=logger,
    )
