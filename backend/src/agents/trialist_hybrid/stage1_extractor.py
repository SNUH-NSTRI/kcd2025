"""
Stage 1: Structured Extraction using Instructor (Function Calling).

Uses OpenAI-compatible Function Calling to extract clinical trial criteria
into structured Pydantic models with automatic validation and retry logic.
"""

import logging
from typing import Optional

import instructor
from openai import OpenAI
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from agents.trialist_hybrid.models import ExtractionOutput
from agents.trialist_hybrid.prompts.extraction_prompt import (
    CORRECTIVE_RETRY_PROMPT,
    SYSTEM_PROMPT,
    build_extraction_prompt,
)

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when extraction fails after all retries."""

    pass


class Stage1Extractor:
    """
    Stage 1: Extract structured entities from raw clinical trial criteria.

    Uses Instructor library for Function Calling with Pydantic models,
    providing automatic validation and retry logic.

    Features:
    - Automatic JSON schema generation from Pydantic models
    - Built-in validation with corrective retry
    - Edge case handling (negation, temporal, assumptions)
    - Empty/irrelevant text gracefully returns empty arrays
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openai/gpt-4o",
        temperature: float = 0.0,
        max_retries: int = 2,
    ):
        """
        Initialize Stage1Extractor with OpenRouter client.

        Args:
            api_key: OpenRouter API key
            base_url: API endpoint (default: OpenRouter)
            model: Model to use (default: gpt-4o via OpenRouter)
            temperature: Sampling temperature (0.0 for deterministic)
            max_retries: Maximum corrective retries on validation errors
        """
        # Create Instructor-wrapped client for Function Calling
        self.client = instructor.from_openai(
            OpenAI(api_key=api_key, base_url=base_url)
        )
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries

    def extract(self, raw_criteria: str) -> ExtractionOutput:
        """
        Extract structured entities from raw criteria text.

        Args:
            raw_criteria: Raw inclusion/exclusion criteria text

        Returns:
            ExtractionOutput with structured CriterionEntity objects

        Raises:
            ExtractionError: If extraction fails after all retries
        """
        if not raw_criteria or not raw_criteria.strip():
            # Handle empty input gracefully
            logger.info("Empty criteria provided, returning empty extraction")
            return ExtractionOutput()

        try:
            # Build extraction prompt
            user_prompt = build_extraction_prompt(raw_criteria)

            # Use Instructor for Function Calling with Pydantic
            # This automatically:
            # 1. Generates JSON schema from ExtractionOutput model
            # 2. Calls LLM with function calling
            # 3. Validates response against Pydantic model
            # 4. Retries on validation errors (up to max_retries)
            extraction = self._extract_with_retry(
                user_prompt=user_prompt,
                raw_criteria=raw_criteria,
            )

            logger.info(
                f"Extracted {len(extraction.inclusion)} inclusion, "
                f"{len(extraction.exclusion)} exclusion criteria"
            )

            return extraction

        except ValidationError as e:
            logger.error(f"Extraction validation failed after retries: {e}")
            raise ExtractionError(
                f"Failed to extract valid entities after {self.max_retries} retries: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected extraction error: {e}")
            raise ExtractionError(f"Extraction failed: {e}")

    def _extract_with_retry(
        self, user_prompt: str, raw_criteria: str
    ) -> ExtractionOutput:
        """
        Extract with exponential backoff retry on API errors.

        Args:
            user_prompt: Formatted extraction prompt
            raw_criteria: Original criteria (for corrective retry)

        Returns:
            ExtractionOutput

        Raises:
            ValidationError: If validation fails after retries
        """
        attempt = 0
        last_error = None

        while attempt <= self.max_retries:
            try:
                # Call LLM with Function Calling via Instructor
                extraction = self.client.chat.completions.create(
                    model=self.model,
                    response_model=ExtractionOutput,  # Pydantic model
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                )

                # Success! Return extraction
                return extraction

            except ValidationError as e:
                # Validation error - try corrective retry
                last_error = e
                attempt += 1

                if attempt > self.max_retries:
                    raise e

                logger.warning(
                    f"Extraction validation failed (attempt {attempt}/{self.max_retries}), "
                    f"retrying with corrective prompt: {e}"
                )

                # Build corrective retry prompt with validation error
                user_prompt = CORRECTIVE_RETRY_PROMPT.format(
                    validation_error=str(e),
                    raw_criteria=raw_criteria,
                )

            except Exception as e:
                # API error - exponential backoff handled by tenacity
                logger.error(f"API error during extraction: {e}")
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise ExtractionError("Extraction failed for unknown reason")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _call_llm_with_backoff(self, messages: list) -> ExtractionOutput:
        """
        Call LLM with exponential backoff on transient API errors.

        This is a wrapper with tenacity retry decorator for handling
        503 errors, timeouts, and other transient failures.

        Args:
            messages: Chat messages for LLM

        Returns:
            ExtractionOutput from LLM

        Raises:
            Exception: If API call fails after retries
        """
        return self.client.chat.completions.create(
            model=self.model,
            response_model=ExtractionOutput,
            messages=messages,
            temperature=self.temperature,
        )
