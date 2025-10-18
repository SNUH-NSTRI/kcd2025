"""
Unit tests for IntelligentMimicMapper

Tests the cascading lookup, LLM integration, validation, and caching logic.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backend.src.pipeline.intelligent_mapper import (
    IntelligentMimicMapper,
    MappingResult,
    MimicMapping,
    AlternativeMapping,
)
from backend.src.pipeline.mimic_schema_reference import get_all_table_names


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_cache_file():
    """Create a temporary cache file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_data = {
            "sepsis_condition": {
                "mapping": {
                    "table": "diagnoses_icd",
                    "columns": ["icd_code", "icd_version"],
                    "filter_logic": "icd_version = 10 AND icd_code LIKE 'A41%' -- Sepsis"
                },
                "confidence": 1.0,
                "reasoning": "Manual mapping from legacy cache",
                "alternatives": [],
                "source": "manual",
                "timestamp": "2025-01-17T10:00:00"
            }
        }
        json.dump(cache_data, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def empty_cache_file():
    """Create an empty cache file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({}, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_openrouter_response():
    """Mock OpenRouter API response."""
    return {
        "mapping": {
            "table": "labevents",
            "columns": ["itemid", "valuenum"],
            "filter_logic": "itemid = 50813 AND valuenum > 2.0 -- Lactate > 2.0 mmol/L"
        },
        "confidence": 0.95,
        "reasoning": "Lactate is measured in labevents with itemid 50813",
        "alternatives": [
            {
                "table": "chartevents",
                "columns": ["itemid", "valuenum"],
                "note": "Some facilities may record lactate in chartevents"
            }
        ]
    }


# ============================================================================
# Test Cache Functionality
# ============================================================================

def test_load_cache_with_existing_data(temp_cache_file):
    """Test loading cache from existing file."""
    mapper = IntelligentMimicMapper(
        mapping_file=temp_cache_file,
        openrouter_api_key="test_key"
    )
    
    assert len(mapper.mapping_cache) == 1
    assert "sepsis_condition" in mapper.mapping_cache


def test_load_cache_with_empty_file(empty_cache_file):
    """Test loading cache from empty file."""
    mapper = IntelligentMimicMapper(
        mapping_file=empty_cache_file,
        openrouter_api_key="test_key"
    )
    
    assert len(mapper.mapping_cache) == 0


def test_load_cache_with_nonexistent_file():
    """Test loading cache when file doesn't exist."""
    nonexistent = Path("/tmp/nonexistent_cache_12345.json")
    mapper = IntelligentMimicMapper(
        mapping_file=nonexistent,
        openrouter_api_key="test_key"
    )
    
    assert len(mapper.mapping_cache) == 0


# ============================================================================
# Test Cache Lookup
# ============================================================================

def test_cache_hit(temp_cache_file):
    """Test successful cache hit."""
    mapper = IntelligentMimicMapper(
        mapping_file=temp_cache_file,
        openrouter_api_key="test_key"
    )
    
    result = mapper._lookup_cache("Sepsis", "Condition")
    
    assert result is not None
    assert result.mapping.table == "diagnoses_icd"
    assert result.confidence == 1.0
    assert result.source == "cache"


def test_cache_miss(temp_cache_file):
    """Test cache miss for unknown concept."""
    mapper = IntelligentMimicMapper(
        mapping_file=temp_cache_file,
        openrouter_api_key="test_key"
    )
    
    result = mapper._lookup_cache("Pneumonia", "Condition")
    
    assert result is None


def test_normalize_concept_key():
    """Test concept key normalization."""
    key = IntelligentMimicMapper._normalize_concept_key("  Sepsis  ", "Condition")
    assert key == "sepsis_condition"
    
    key = IntelligentMimicMapper._normalize_concept_key("Heart Failure", "Condition")
    assert key == "heart_failure_condition"


# ============================================================================
# Test Validation
# ============================================================================

def test_validate_valid_mapping(temp_cache_file):
    """Test validation of valid mapping."""
    mapper = IntelligentMimicMapper(
        mapping_file=temp_cache_file,
        openrouter_api_key="test_key"
    )
    
    result = MappingResult(
        mapping=MimicMapping(
            table="labevents",
            columns=["itemid", "valuenum"],
            filter_logic="itemid = 50813"
        ),
        confidence=0.9,
        reasoning="Valid mapping",
        source="llm"
    )
    
    assert mapper._validate_mapping(result) is True


def test_validate_invalid_table(temp_cache_file):
    """Test validation fails for invalid table name (Pydantic catches it first)."""
    mapper = IntelligentMimicMapper(
        mapping_file=temp_cache_file,
        openrouter_api_key="test_key"
    )

    # Pydantic validation will raise error before _validate_mapping is called
    try:
        result = MappingResult(
            mapping=MimicMapping(
                table="fake_table",
                columns=["value"],
                filter_logic="-- fake"
            ),
            confidence=0.9,
            reasoning="Invalid table",
            source="llm"
        )
        # If we get here, validation didn't work
        assert False, "Expected Pydantic validation error"
    except Exception as e:
        # Expected: Pydantic catches invalid table name
        assert "Invalid MIMIC table" in str(e) or "ValidationError" in str(type(e))


def test_validate_invalid_confidence(temp_cache_file):
    """Test validation fails for out-of-range confidence (Pydantic catches it first)."""
    mapper = IntelligentMimicMapper(
        mapping_file=temp_cache_file,
        openrouter_api_key="test_key"
    )

    # Pydantic validation will raise error before _validate_mapping is called
    try:
        result = MappingResult(
            mapping=MimicMapping(
                table="labevents",
                columns=["itemid"],
                filter_logic="itemid = 50813"
            ),
            confidence=1.5,  # Invalid: > 1.0
            reasoning="Invalid confidence",
            source="llm"
        )
        # If we get here, validation didn't work
        assert False, "Expected Pydantic validation error"
    except Exception as e:
        # Expected: Pydantic catches invalid confidence
        assert "less than or equal to 1" in str(e) or "ValidationError" in str(type(e))


# ============================================================================
# Test LLM Integration (Mocked)
# ============================================================================

@patch('backend.src.pipeline.intelligent_mapper.httpx.Client')
def test_llm_map_success(mock_httpx_client, empty_cache_file, mock_openrouter_response):
    """Test successful LLM mapping."""
    # Mock HTTP response
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(mock_openrouter_response)
            }
        }]
    }
    mock_response.raise_for_status = Mock()
    
    mock_client_instance = Mock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = Mock(return_value=False)
    mock_httpx_client.return_value = mock_client_instance
    
    mapper = IntelligentMimicMapper(
        mapping_file=empty_cache_file,
        openrouter_api_key="test_key"
    )
    
    result = mapper._llm_map("Lactate", "Measurement")
    
    assert result is not None
    assert result.mapping.table == "labevents"
    assert result.confidence == 0.95
    assert result.source == "llm"
    assert len(result.alternatives) == 1


@patch('backend.src.pipeline.intelligent_mapper.httpx.Client')
def test_llm_map_api_failure(mock_httpx_client, empty_cache_file):
    """Test LLM mapping handles API failure."""
    mock_client_instance = Mock()
    mock_client_instance.post.side_effect = Exception("API Error")
    mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = Mock(return_value=False)
    mock_httpx_client.return_value = mock_client_instance
    
    mapper = IntelligentMimicMapper(
        mapping_file=empty_cache_file,
        openrouter_api_key="test_key"
    )
    
    result = mapper._llm_map("Lactate", "Measurement")
    
    assert result is None


# ============================================================================
# Test Full Mapping Flow
# ============================================================================

def test_map_concept_cache_hit(temp_cache_file):
    """Test map_concept returns cached result."""
    mapper = IntelligentMimicMapper(
        mapping_file=temp_cache_file,
        openrouter_api_key="test_key"
    )
    
    result = mapper.map_concept("Sepsis", "Condition")
    
    assert result.mapping.table == "diagnoses_icd"
    assert result.source == "cache"
    assert result.confidence == 1.0


@patch('backend.src.pipeline.intelligent_mapper.httpx.Client')
def test_map_concept_cache_miss_llm_success(
    mock_httpx_client, 
    empty_cache_file, 
    mock_openrouter_response
):
    """Test map_concept falls back to LLM on cache miss."""
    # Mock HTTP response
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(mock_openrouter_response)
            }
        }]
    }
    mock_response.raise_for_status = Mock()
    
    mock_client_instance = Mock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = Mock(return_value=False)
    mock_httpx_client.return_value = mock_client_instance
    
    mapper = IntelligentMimicMapper(
        mapping_file=empty_cache_file,
        openrouter_api_key="test_key"
    )
    
    result = mapper.map_concept("Lactate", "Measurement")
    
    assert result.mapping.table == "labevents"
    assert result.source == "llm"
    assert result.confidence == 0.95
    
    # Verify cache was updated
    assert "lactate_measurement" in mapper.mapping_cache


@patch('backend.src.pipeline.intelligent_mapper.httpx.Client')
def test_map_concept_llm_failure_fallback(mock_httpx_client, empty_cache_file):
    """Test map_concept returns fallback on LLM failure."""
    mock_client_instance = Mock()
    mock_client_instance.post.side_effect = Exception("API Error")
    mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = Mock(return_value=False)
    mock_httpx_client.return_value = mock_client_instance
    
    mapper = IntelligentMimicMapper(
        mapping_file=empty_cache_file,
        openrouter_api_key="test_key"
    )
    
    result = mapper.map_concept("Unknown", "Measurement")
    
    assert result.confidence == 0.0
    assert result.source == "fallback"
    assert "manual mapping required" in result.mapping.filter_logic.lower()


# ============================================================================
# Test Pydantic Models
# ============================================================================

def test_mimic_mapping_validation():
    """Test MimicMapping validates table names."""
    # Valid table
    mapping = MimicMapping(
        table="labevents",
        columns=["itemid"],
        filter_logic="itemid = 50813"
    )
    assert mapping.table == "labevents"
    
    # Invalid table should raise ValidationError
    with pytest.raises(Exception):  # Pydantic ValidationError
        MimicMapping(
            table="invalid_table",
            columns=["value"],
            filter_logic="-- invalid"
        )


def test_mapping_result_to_dict():
    """Test MappingResult serialization."""
    result = MappingResult(
        mapping=MimicMapping(
            table="labevents",
            columns=["itemid", "valuenum"],
            filter_logic="itemid = 50813"
        ),
        confidence=0.9,
        reasoning="Test mapping",
        alternatives=[],
        source="test"
    )
    
    data = result.to_dict()
    
    assert data["mapping"]["table"] == "labevents"
    assert data["confidence"] == 0.9
    assert data["source"] == "test"
    assert "timestamp" in data


# ============================================================================
# Integration Test Markers
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not Path("backend/src/pipeline/mimic_concept_mapping_v2.json").exists(),
    reason="Migrated cache file not found"
)
def test_real_cache_integration():
    """Integration test with actual migrated cache."""
    cache_file = Path("backend/src/pipeline/mimic_concept_mapping_v2.json")
    
    mapper = IntelligentMimicMapper(
        mapping_file=cache_file,
        openrouter_api_key="dummy"  # Won't be used for cache hits
    )
    
    # Test known cached concept
    result = mapper.map_concept("Heart Failure", "Condition")
    
    assert result is not None
    assert result.source == "cache"
    assert result.mapping.table == "diagnoses_icd"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
