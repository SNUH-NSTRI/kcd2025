"""
Stage 2: MIMIC-IV Mapping using Instructor (Function Calling).

Maps extracted CriterionEntity objects to MIMIC-IV database schema
with strict validation against actual table/column names.
"""

import json
import logging
from pathlib import Path
from typing import Dict

import instructor
from openai import OpenAI
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from agents.trialist_hybrid.models import CriterionEntity, MappingOutput
from agents.trialist_hybrid.prompts.mapping_prompt import (
    CORRECTIVE_RETRY_PROMPT,
    SYSTEM_PROMPT,
    build_mapping_prompt,
    load_schema_with_context,
)
from agents.trialist_hybrid.shared_cache import SharedCriterionCache

logger = logging.getLogger(__name__)


class MappingError(Exception):
    """Raised when mapping fails after all retries."""

    pass


class Stage2Mapper:
    """
    Stage 2: Map extracted entities to MIMIC-IV database schema.

    Features:
    - Strict validation against MIMIC-IV schema
    - Automatic ICD code enrichment for diagnoses
    - Itemid mapping for lab values and vital signs
    - Temporal constraint handling
    - Confidence scoring based on mapping quality
    """

    def __init__(
        self,
        api_key: str,
        schema_path: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openai/gpt-4o",
        temperature: float = 0.0,
        max_retries: int = 2,
        cache_dir: Path = None,
        use_cache: bool = True,
    ):
        """
        Initialize Stage2Mapper.

        Args:
            api_key: OpenRouter API key
            schema_path: Path to MIMIC-IV schema JSON file
            base_url: API endpoint (default: OpenRouter)
            model: Model to use (default: gpt-4o)
            temperature: Sampling temperature (0.0 for deterministic)
            max_retries: Maximum corrective retries
            cache_dir: Directory for shared cache (default: schema_path/../cache)
            use_cache: Whether to use shared cache (default: True)
        """
        self.client = instructor.from_openai(
            OpenAI(api_key=api_key, base_url=base_url)
        )
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.schema_path = schema_path

        # Load full MIMIC-IV schema
        self.schema = self._load_mimic_schema(schema_path)

        # Initialize shared cache
        self.use_cache = use_cache
        if use_cache:
            if cache_dir is None:
                cache_dir = Path(schema_path).parent.parent.parent.parent / "cache"
            self.cache = SharedCriterionCache(cache_dir)
        else:
            self.cache = None

    def _load_mimic_schema(self, schema_path: str) -> Dict:
        """Load MIMIC-IV schema from JSON file."""
        with open(schema_path, "r") as f:
            return json.load(f)

    def map_to_mimic(self, entity: CriterionEntity) -> MappingOutput:
        """
        Map criterion entity to MIMIC-IV database schema.

        Uses shared cache to avoid redundant LLM calls.

        Args:
            entity: CriterionEntity from Stage 1

        Returns:
            MappingOutput with MIMIC-IV mapping and confidence

        Raises:
            MappingError: If mapping fails after all retries
        """
        # Check cache first
        if self.use_cache and self.cache:
            cached_mapping = self.cache.get(entity.text)
            if cached_mapping:
                logger.info(f"⚡ Cache HIT for '{entity.text}' (criterion {entity.id})")
                # Reconstruct MappingOutput from cached data
                return MappingOutput(
                    criterion=entity,
                    mimic_mapping=cached_mapping["mimic_mapping"],
                    confidence=cached_mapping["confidence"],
                    reasoning=cached_mapping["reasoning"] + " [CACHED]"
                )

        logger.info(f"🔄 Cache MISS for '{entity.text}', calling LLM...")

        try:
            # Get schema context filtered by entity type
            schema_json = load_schema_with_context(
                self.schema_path, entity.entity_type
            )

            # Build mapping prompt
            entity_json = entity.model_dump_json(indent=2)
            user_prompt = build_mapping_prompt(entity_json, schema_json)

            # Map with retry logic
            mapping = self._map_with_retry(
                user_prompt=user_prompt,
                entity_json=entity_json,
                schema_json=schema_json,
            )

            # Validate against schema and adjust confidence
            if not self._validate_against_schema(mapping):
                logger.warning(
                    f"Schema validation failed for {entity.id}, reducing confidence"
                )
                # Reduce confidence significantly for invalid schema
                mapping.confidence = min(mapping.confidence * 0.5, 0.5)

            # Save to cache
            if self.use_cache and self.cache:
                self.cache.set(
                    criterion_text=entity.text,
                    mapping={
                        "mimic_mapping": mapping.mimic_mapping.model_dump(),
                        "confidence": mapping.confidence,
                        "reasoning": mapping.reasoning
                    },
                    validated=False  # Mark as unvalidated initially
                )
                logger.info(f"💾 Saved mapping for '{entity.text}' to cache")

            logger.info(
                f"Mapped {entity.id} to {mapping.mimic_mapping.table} "
                f"(confidence: {mapping.confidence:.2f})"
            )

            return mapping

        except ValidationError as e:
            logger.error(f"Mapping validation failed: {e}")
            raise MappingError(f"Failed to map entity {entity.id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected mapping error: {e}")
            raise MappingError(f"Mapping failed: {e}")

    def _map_with_retry(
        self, user_prompt: str, entity_json: str, schema_json: str
    ) -> MappingOutput:
        """
        Map with corrective retry on validation errors.

        Args:
            user_prompt: Initial mapping prompt
            entity_json: Original entity JSON
            schema_json: MIMIC schema JSON

        Returns:
            MappingOutput

        Raises:
            ValidationError: If validation fails after retries
        """
        attempt = 0
        last_error = None

        while attempt <= self.max_retries:
            try:
                # Call LLM with Function Calling
                mapping = self.client.chat.completions.create(
                    model=self.model,
                    response_model=MappingOutput,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                )

                return mapping

            except ValidationError as e:
                last_error = e
                attempt += 1

                if attempt > self.max_retries:
                    raise e

                logger.warning(
                    f"Mapping validation failed (attempt {attempt}/{self.max_retries}), "
                    f"retrying with corrective prompt: {e}"
                )

                # Build corrective retry prompt
                user_prompt = CORRECTIVE_RETRY_PROMPT.format(
                    validation_error=str(e),
                    entity_json=entity_json,
                    schema_json=schema_json,
                )

            except Exception as e:
                logger.error(f"API error during mapping: {e}")
                raise

        if last_error:
            raise last_error
        raise MappingError("Mapping failed for unknown reason")

    def _validate_against_schema(self, mapping: MappingOutput) -> bool:
        """
        Validate mapping against MIMIC-IV schema.

        Checks:
        1. Table exists in schema
        2. All columns exist in specified table
        3. Join table exists (if specified)

        Args:
            mapping: MappingOutput to validate

        Returns:
            True if valid, False otherwise
        """
        mimic_mapping = mapping.mimic_mapping

        # Check table exists
        table = mimic_mapping.table
        if table not in self.schema["tables"]:
            logger.warning(f"Invalid table: {table} not in schema")
            return False

        # Check columns exist in table
        valid_columns = self.schema["tables"][table]["columns"]
        for col in mimic_mapping.columns:
            if col not in valid_columns:
                logger.warning(
                    f"Invalid column: {col} not in {table}. "
                    f"Valid columns: {valid_columns}"
                )
                return False

        # Check join table if specified
        if mimic_mapping.join_table:
            if mimic_mapping.join_table not in self.schema["tables"]:
                logger.warning(f"Invalid join table: {mimic_mapping.join_table}")
                return False

            # Check join columns
            if mimic_mapping.join_columns:
                join_valid_columns = self.schema["tables"][mimic_mapping.join_table][
                    "columns"
                ]
                for col in mimic_mapping.join_columns:
                    if col not in join_valid_columns:
                        logger.warning(
                            f"Invalid join column: {col} not in {mimic_mapping.join_table}"
                        )
                        return False

        logger.debug(f"Schema validation passed for {table}")
        return True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _call_llm_with_backoff(self, messages: list) -> MappingOutput:
        """
        Call LLM with exponential backoff for transient errors.

        Args:
            messages: Chat messages

        Returns:
            MappingOutput

        Raises:
            Exception: If API call fails after retries
        """
        return self.client.chat.completions.create(
            model=self.model,
            response_model=MappingOutput,
            messages=messages,
            temperature=self.temperature,
        )
