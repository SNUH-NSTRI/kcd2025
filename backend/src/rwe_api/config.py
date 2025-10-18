"""Centralized configuration module for RWE API.

This module provides a SINGLE SOURCE OF TRUTH for all environment variables
and application configuration. It ALWAYS loads .env files correctly using
multiple fallback strategies.

Following Zen principles:
- Load once, use everywhere
- Fail fast with clear messages
- No surprises, predictable behavior

Usage:
    from rwe_api.config import settings

    # Access configuration
    api_key = settings.OPENROUTER_API_KEY
    workspace = settings.WORKSPACE_ROOT
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# Zen Environment Loading Strategy
# =============================================================================
# ALWAYS finds and loads .env file using multiple strategies:
# 1. backend/.env (new canonical location)
# 2. project_root/.env (legacy location)
# 3. Environment variables (CI/CD, Docker)
# =============================================================================

def _find_and_load_dotenv() -> Path | None:
    """Find and load .env file using multiple strategies.

    Strategy 1: backend/.env (canonical location)
    Strategy 2: project_root/.env (legacy, will be deprecated)

    Returns:
        Path to loaded .env file, or None if not found
    """
    # Get backend directory (this file is in backend/src/rwe_api/)
    backend_dir = Path(__file__).parent.parent.parent

    # Strategy 1: backend/.env (NEW - canonical location)
    backend_env = backend_dir / ".env"
    if backend_env.exists():
        load_dotenv(backend_env, override=True)
        print(f"✅ Loaded environment from: {backend_env}", file=sys.stderr)
        return backend_env

    # Strategy 2: project_root/.env (LEGACY - for backward compatibility)
    project_root = backend_dir.parent
    root_env = project_root / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=True)
        print(f"⚠️  Loaded environment from LEGACY location: {root_env}", file=sys.stderr)
        print(f"⚠️  Please move .env to: {backend_env}", file=sys.stderr)
        return root_env

    # Strategy 3: Environment variables (no .env file)
    print("⚠️  No .env file found - using system environment variables", file=sys.stderr)
    return None


# Load .env file IMMEDIATELY on module import (singleton pattern)
_DOTENV_PATH = _find_and_load_dotenv()


class Settings(BaseSettings):
    """Application settings with automatic environment variable loading.

    This class uses Pydantic Settings to:
    1. Load from .env file (already loaded above)
    2. Load from environment variables
    3. Provide type validation
    4. Provide sensible defaults

    Attributes:
        OPENROUTER_API_KEY: OpenRouter API key for LLM services
        WORKSPACE_ROOT: Root directory for project data
        PROJECT_ROOT: Alias for WORKSPACE_ROOT (backward compatibility)
        CORS_ORIGINS: Comma-separated list of allowed CORS origins
        FASTAPI_DEBUG: Enable FastAPI debug mode
        FASTAPI_PORT: FastAPI server port
        FASTAPI_HOST: FastAPI server host
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    model_config = SettingsConfigDict(
        # Load from environment variables (case-insensitive)
        env_file=None,  # Already loaded by _find_and_load_dotenv()
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =============================================================================
    # LLM API Configuration
    # =============================================================================
    OPENROUTER_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenRouter API key for LLM services",
        validation_alias="OPENROUTER_API_KEY",
    )

    # =============================================================================
    # Workspace Configuration
    # =============================================================================
    WORKSPACE_ROOT: Path = Field(
        default=Path.cwd() / "project",
        description="Root directory for project data",
        validation_alias="WORKSPACE_ROOT",
    )

    PROJECT_ROOT: Optional[Path] = Field(
        default=None,
        description="Alias for WORKSPACE_ROOT (backward compatibility)",
        validation_alias="PROJECT_ROOT",
    )

    # =============================================================================
    # CORS Configuration
    # =============================================================================
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins",
        validation_alias="CORS_ORIGINS",
    )

    # =============================================================================
    # FastAPI Configuration
    # =============================================================================
    FASTAPI_DEBUG: bool = Field(
        default=False,
        description="Enable FastAPI debug mode",
        validation_alias="FASTAPI_DEBUG",
    )

    FASTAPI_PORT: int = Field(
        default=8000,
        description="FastAPI server port",
        validation_alias="FASTAPI_PORT",
    )

    FASTAPI_HOST: str = Field(
        default="0.0.0.0",
        description="FastAPI server host",
        validation_alias="FASTAPI_HOST",
    )

    # =============================================================================
    # Logging Configuration
    # =============================================================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level",
        validation_alias="LOG_LEVEL",
    )

    def model_post_init(self, __context) -> None:
        """Post-initialization validation and setup."""
        # Ensure PROJECT_ROOT is set (backward compatibility)
        if self.PROJECT_ROOT is None:
            object.__setattr__(self, "PROJECT_ROOT", self.WORKSPACE_ROOT)

        # Ensure workspace directory exists
        self.WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

        # Log configuration status
        print(f"📁 Workspace: {self.WORKSPACE_ROOT}", file=sys.stderr)
        if self.OPENROUTER_API_KEY:
            print(f"🔑 OpenRouter API key: {'*' * 20}{self.OPENROUTER_API_KEY[-8:]}", file=sys.stderr)
        else:
            print("⚠️  OpenRouter API key: NOT SET", file=sys.stderr)

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def validate_openrouter_key(self) -> tuple[bool, str]:
        """Validate that OpenRouter API key is set.

        Returns:
            (is_valid, error_message)
        """
        if not self.OPENROUTER_API_KEY:
            return False, (
                "OPENROUTER_API_KEY not provided. "
                "Set environment variable or add to .env file."
            )
        return True, ""

    def get_env_file_path(self) -> Path | None:
        """Get path to loaded .env file.

        Returns:
            Path to .env file, or None if using system environment
        """
        return _DOTENV_PATH


# =============================================================================
# Global Settings Instance (Singleton)
# =============================================================================
# This is the ONLY instance you should use throughout the application
settings = Settings()


# =============================================================================
# Backward Compatibility Helpers
# =============================================================================
def get_workspace_root() -> Path:
    """Get workspace root directory.

    Returns:
        Path to workspace root
    """
    return settings.WORKSPACE_ROOT


def get_openrouter_api_key() -> str | None:
    """Get OpenRouter API key.

    Returns:
        API key or None if not set
    """
    return settings.OPENROUTER_API_KEY


# =============================================================================
# Module Initialization
# =============================================================================
if __name__ == "__main__":
    # Print configuration when run as script
    print("=" * 80)
    print("RWE API Configuration")
    print("=" * 80)
    print(f"Loaded .env from: {settings.get_env_file_path() or 'System environment'}")
    print(f"WORKSPACE_ROOT: {settings.WORKSPACE_ROOT}")
    print(f"PROJECT_ROOT: {settings.PROJECT_ROOT}")
    print(f"CORS_ORIGINS: {settings.CORS_ORIGINS}")
    print(f"FASTAPI_DEBUG: {settings.FASTAPI_DEBUG}")
    print(f"FASTAPI_PORT: {settings.FASTAPI_PORT}")
    print(f"FASTAPI_HOST: {settings.FASTAPI_HOST}")
    print(f"LOG_LEVEL: {settings.LOG_LEVEL}")
    print(f"OPENROUTER_API_KEY: {'SET' if settings.OPENROUTER_API_KEY else 'NOT SET'}")
    print("=" * 80)

    # Validate
    is_valid, error = settings.validate_openrouter_key()
    if not is_valid:
        print(f"❌ Validation failed: {error}")
        sys.exit(1)
    else:
        print("✅ All required configuration is valid")
