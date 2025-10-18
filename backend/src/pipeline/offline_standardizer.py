"""
Offline Standardizer for Trialist Stage 2: Component Standardization

Provides offline concept normalization and temporal pattern standardization
without requiring external UMLS/OHDSI API calls.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher
from dataclasses import dataclass

from .trialist_models import EnhancedNamedEntity, TemporalRelation


@dataclass
class StandardizedConcept:
    """Standardized medical concept."""
    original_text: str
    standard_name: str
    umls_cui: Optional[str] = None
    code_system: Optional[str] = None
    primary_code: Optional[str] = None
    confidence: float = 0.8
    synonyms: List[str] = None
    
    def __post_init__(self):
        if self.synonyms is None:
            self.synonyms = []


class OfflineStandardizer:
    """
    Offline medical concept standardizer using pre-built vocabularies.
    
    This implementation provides basic standardization capabilities without
    requiring external API calls to UMLS or OHDSI services.
    """
    
    def __init__(self):
        self.concept_mappings = self._build_concept_mappings()
        self.temporal_patterns = self._build_temporal_patterns()
        self.domain_vocabularies = self._build_domain_vocabularies()
        self.abbreviation_map = self._build_abbreviation_map()
        
    def _build_concept_mappings(self) -> Dict[str, Dict[str, StandardizedConcept]]:
        """Build domain-specific concept mappings."""
        mappings = {
            "Condition": {
                # Cardiovascular conditions - Core
                "heart failure": StandardizedConcept(
                    original_text="heart failure",
                    standard_name="Heart failure",
                    umls_cui="C0018801",
                    code_system="SNOMED",
                    primary_code="84114007",
                    confidence=0.95,
                    synonyms=["cardiac failure", "congestive heart failure", "CHF"]
                ),
                "chronic heart failure": StandardizedConcept(
                    original_text="chronic heart failure",
                    standard_name="Chronic heart failure",
                    umls_cui="C0264716",
                    code_system="SNOMED",
                    primary_code="48447003",
                    confidence=0.95,
                    synonyms=["CHF"]
                ),
                "hfpef": StandardizedConcept(
                    original_text="hfpef",
                    standard_name="Heart failure with preserved ejection fraction",
                    umls_cui="C3864734",
                    code_system="SNOMED",
                    primary_code="703272007",
                    confidence=0.95,
                    synonyms=["heart failure with preserved ejection fraction", "diastolic heart failure"]
                ),
                "diastolic dysfunction": StandardizedConcept(
                    original_text="diastolic dysfunction",
                    standard_name="Diastolic dysfunction",
                    umls_cui="C0520863",
                    code_system="SNOMED",
                    primary_code="48431000119100",
                    confidence=0.95,
                    synonyms=["lv diastolic dysfunction"]
                ),
                "myocardial infarction": StandardizedConcept(
                    original_text="myocardial infarction",
                    standard_name="Myocardial infarction",
                    umls_cui="C0027051",
                    code_system="SNOMED",
                    primary_code="22298006",
                    confidence=0.95,
                    synonyms=["heart attack", "MI", "cardiac infarction"]
                ),
                "acute coronary syndrome": StandardizedConcept(
                    original_text="acute coronary syndrome",
                    standard_name="Acute coronary syndrome",
                    umls_cui="C0948089",
                    code_system="SNOMED",
                    primary_code="394659003",
                    confidence=0.95,
                    synonyms=["ACS"]
                ),
                "stroke": StandardizedConcept(
                    original_text="stroke",
                    standard_name="Cerebrovascular accident",
                    umls_cui="C0038454",
                    code_system="SNOMED",
                    primary_code="230690007",
                    confidence=0.95,
                    synonyms=["cerebrovascular accident", "CVA", "brain attack", "tia/cva"]
                ),
                "hypertension": StandardizedConcept(
                    original_text="hypertension",
                    standard_name="Hypertensive disorder",
                    umls_cui="C0020538",
                    code_system="SNOMED",
                    primary_code="38341003",
                    confidence=0.95,
                    synonyms=["high blood pressure", "HTN"]
                ),
                "diabetes": StandardizedConcept(
                    original_text="diabetes",
                    standard_name="Diabetes mellitus",
                    umls_cui="C0011849",
                    code_system="SNOMED",
                    primary_code="73211009",
                    confidence=0.95,
                    synonyms=["diabetes mellitus", "DM"]
                ),
                "kidney disease": StandardizedConcept(
                    original_text="kidney disease",
                    standard_name="Kidney disease",
                    umls_cui="C0022658",
                    code_system="SNOMED",
                    primary_code="90708001",
                    confidence=0.95,
                    synonyms=["renal disease", "severe kidney disease"]
                ),
                "liver insufficiency": StandardizedConcept(
                    original_text="liver insufficiency",
                    standard_name="Hepatic insufficiency",
                    umls_cui="C0151763",
                    code_system="SNOMED",
                    primary_code="59927004",
                    confidence=0.95,
                    synonyms=["hepatic failure", "liver failure", "severe liver insufficiency"]
                ),
                "pregnancy": StandardizedConcept(
                    original_text="pregnancy",
                    standard_name="Pregnancy",
                    umls_cui="C0032961",
                    code_system="SNOMED",
                    primary_code="77386006",
                    confidence=0.95
                ),
                "hypersensitivity": StandardizedConcept(
                    original_text="hypersensitivity",
                    standard_name="Hypersensitivity reaction",
                    umls_cui="C0020517",
                    code_system="SNOMED",
                    primary_code="609433001",
                    confidence=0.95,
                    synonyms=["allergy", "allergic reaction"]
                ),
                "ketoacidosis": StandardizedConcept(
                    original_text="ketoacidosis",
                    standard_name="Ketoacidosis",
                    umls_cui="C0220982",
                    code_system="SNOMED",
                    primary_code="9619003",
                    confidence=0.95,
                    synonyms=["risk of ketoacidosis"]
                ),
                "cancer": StandardizedConcept(
                    original_text="cancer",
                    standard_name="Malignant neoplasm",
                    umls_cui="C0006826",
                    code_system="SNOMED",
                    primary_code="363346000",
                    confidence=0.90,
                    synonyms=["malignancy", "tumor", "neoplasm"]
                ),
                # Neurological conditions
                "traumatic brain injury": StandardizedConcept(
                    original_text="traumatic brain injury",
                    standard_name="Traumatic brain injury",
                    umls_cui="C0876926",
                    code_system="SNOMED",
                    primary_code="127295002",
                    confidence=0.95,
                    synonyms=["TBI", "head injury", "brain trauma"]
                ),
                "seizure": StandardizedConcept(
                    original_text="seizure",
                    standard_name="Seizure disorder",
                    umls_cui="C0036572",
                    code_system="SNOMED",
                    primary_code="91175000",
                    confidence=0.95,
                    synonyms=["convulsion", "epileptic seizure"]
                ),
            },
            
            "Drug": {
                "empagliflozin": StandardizedConcept(
                    original_text="empagliflozin",
                    standard_name="Empagliflozin",
                    umls_cui="C3490348",
                    code_system="RxNorm",
                    primary_code="1545653",
                    confidence=0.95,
                    synonyms=["jardiance", "treatment with empagliflozin", "use of empagliflozin"]
                ),
                "sglt-2 inhibitor": StandardizedConcept(
                    original_text="sglt-2 inhibitor",
                    standard_name="Sodium-glucose cotransporter 2 inhibitor",
                    umls_cui="C3273807",
                    code_system="RxNorm",
                    primary_code="1488564",
                    confidence=0.95,
                    synonyms=["sglt2 inhibitor", "other sglt-2 inhibitor"]
                ),
                "aspirin": StandardizedConcept(
                    original_text="aspirin",
                    standard_name="Aspirin",
                    umls_cui="C0004057",
                    code_system="RxNorm",
                    primary_code="1191",
                    confidence=0.95,
                    synonyms=["acetylsalicylic acid", "ASA"]
                ),
                "warfarin": StandardizedConcept(
                    original_text="warfarin",
                    standard_name="Warfarin",
                    umls_cui="C0043031",
                    code_system="RxNorm",
                    primary_code="11289",
                    confidence=0.95,
                    synonyms=["coumadin"]
                ),
                "metformin": StandardizedConcept(
                    original_text="metformin",
                    standard_name="Metformin",
                    umls_cui="C0025598",
                    code_system="RxNorm",
                    primary_code="6809",
                    confidence=0.95,
                    synonyms=["glucophage"]
                ),
                "insulin": StandardizedConcept(
                    original_text="insulin",
                    standard_name="Insulin",
                    umls_cui="C0021641",
                    code_system="RxNorm",
                    primary_code="5856",
                    confidence=0.95
                ),
                "acetylcholine": StandardizedConcept(
                    original_text="acetylcholine",
                    standard_name="Acetylcholine",
                    umls_cui="C0001041",
                    code_system="RxNorm",
                    primary_code="167",
                    confidence=0.95
                ),
                "sodium nitroprusside": StandardizedConcept(
                    original_text="sodium nitroprusside",
                    standard_name="Sodium nitroprusside",
                    umls_cui="C0037533",
                    code_system="RxNorm",
                    primary_code="9887",
                    confidence=0.95,
                    synonyms=["nitroprusside"]
                ),
            },
            
            "Measurement": {
                # Cardiac measurements
                "natriuretic peptide": StandardizedConcept(
                    original_text="natriuretic peptide",
                    standard_name="Natriuretic peptide",
                    umls_cui="C0027481",
                    code_system="LOINC",
                    primary_code="83107-3",
                    confidence=0.95,
                    synonyms=["bnp", "raised natriuretic peptides"]
                ),
                "pulmonary capillary wedge pressure": StandardizedConcept(
                    original_text="pulmonary capillary wedge pressure",
                    standard_name="Pulmonary capillary wedge pressure",
                    umls_cui="C0034091",
                    code_system="LOINC",
                    primary_code="8403-2",
                    confidence=0.95,
                    synonyms=["pcwp", "invasively measured pulmonary capillary wedge pressure"]
                ),
                "left ventricular end diastolic pressure": StandardizedConcept(
                    original_text="left ventricular end diastolic pressure",
                    standard_name="Left ventricular end diastolic pressure",
                    umls_cui="C0428883",
                    code_system="LOINC",
                    primary_code="8480-6",
                    confidence=0.95,
                    synonyms=["lvedp"]
                ),
                "ejection fraction": StandardizedConcept(
                    original_text="ejection fraction",
                    standard_name="Ejection fraction",
                    umls_cui="C0489482",
                    code_system="LOINC",
                    primary_code="10230-1",
                    confidence=0.95,
                    synonyms=["lvef", "left ventricular ejection fraction"]
                ),
                "vascular conductance": StandardizedConcept(
                    original_text="vascular conductance",
                    standard_name="Vascular conductance",
                    umls_cui="C0429863",
                    code_system="LOINC",
                    primary_code="8462-4",
                    confidence=0.95,
                    synonyms=["cutaneous vascular conductance", "cvc"]
                ),
                "blood pressure": StandardizedConcept(
                    original_text="blood pressure",
                    standard_name="Blood pressure",
                    umls_cui="C0005823",
                    code_system="LOINC",
                    primary_code="85354-9",
                    confidence=0.95,
                    synonyms=["BP"]
                ),
                "systolic blood pressure": StandardizedConcept(
                    original_text="systolic blood pressure",
                    standard_name="Systolic blood pressure",
                    umls_cui="C0871470",
                    code_system="LOINC",
                    primary_code="8480-6",
                    confidence=0.95,
                    synonyms=["systolic BP", "SBP"]
                ),
                "diastolic blood pressure": StandardizedConcept(
                    original_text="diastolic blood pressure",
                    standard_name="Diastolic blood pressure",
                    umls_cui="C0428883",
                    code_system="LOINC",
                    primary_code="8462-4",
                    confidence=0.95,
                    synonyms=["diastolic BP", "DBP"]
                ),
                "heart rate": StandardizedConcept(
                    original_text="heart rate",
                    standard_name="Heart rate",
                    umls_cui="C0018810",
                    code_system="LOINC",
                    primary_code="8867-4",
                    confidence=0.95,
                    synonyms=["pulse rate", "HR"]
                ),
                "glucose": StandardizedConcept(
                    original_text="glucose",
                    standard_name="Glucose measurement",
                    umls_cui="C0017725",
                    code_system="LOINC",
                    primary_code="2345-7",
                    confidence=0.95,
                    synonyms=["blood glucose", "blood sugar"]
                ),
                "hemoglobin": StandardizedConcept(
                    original_text="hemoglobin",
                    standard_name="Hemoglobin",
                    umls_cui="C0019046",
                    code_system="LOINC",
                    primary_code="718-7",
                    confidence=0.95,
                    synonyms=["Hgb", "Hb"]
                ),
                "creatinine": StandardizedConcept(
                    original_text="creatinine",
                    standard_name="Creatinine",
                    umls_cui="C0010294",
                    code_system="LOINC",
                    primary_code="2160-0",
                    confidence=0.95
                ),
                "glomerular filtration rate": StandardizedConcept(
                    original_text="glomerular filtration rate",
                    standard_name="Glomerular filtration rate",
                    umls_cui="C0017654",
                    code_system="LOINC",
                    primary_code="33914-3",
                    confidence=0.95,
                    synonyms=["gfr", "egfr"]
                ),
            },
            
            "Procedure": {
                "coronary artery bypass grafting": StandardizedConcept(
                    original_text="coronary artery bypass grafting",
                    standard_name="Coronary artery bypass graft",
                    umls_cui="C0010055",
                    code_system="ICD10PCS",
                    primary_code="021009W",
                    confidence=0.95,
                    synonyms=["cabg", "bypass surgery"]
                ),
                "cardiac valve replacement": StandardizedConcept(
                    original_text="cardiac valve replacement",
                    standard_name="Heart valve replacement",
                    umls_cui="C0190173",
                    code_system="ICD10PCS",
                    primary_code="02RF08Z",
                    confidence=0.95,
                    synonyms=["valve replacement"]
                ),
                "major surgery": StandardizedConcept(
                    original_text="major surgery",
                    standard_name="Major surgical procedure",
                    umls_cui="C0205082",
                    code_system="ICD10PCS",
                    primary_code="0W9Q00Z",
                    confidence=0.90,
                    synonyms=["recent major surgery", "planned major surgery"]
                ),
                "informed consent": StandardizedConcept(
                    original_text="informed consent",
                    standard_name="Informed consent",
                    umls_cui="C0021430",
                    code_system="SNOMED",
                    primary_code="386053000",
                    confidence=0.95,
                    synonyms=["signed informed consent", "consent"]
                ),
                "cardiac catheterization": StandardizedConcept(
                    original_text="cardiac catheterization",
                    standard_name="Cardiac catheterization",
                    umls_cui="C0018795",
                    code_system="ICD10PCS",
                    primary_code="02183ZZ",
                    confidence=0.95
                ),
                "coronary angioplasty": StandardizedConcept(
                    original_text="coronary angioplasty",
                    standard_name="Percutaneous coronary intervention",
                    umls_cui="C1532338",
                    code_system="ICD10PCS",
                    primary_code="02703ZZ",
                    confidence=0.95,
                    synonyms=["PCI", "balloon angioplasty"]
                ),
                "dialysis": StandardizedConcept(
                    original_text="dialysis",
                    standard_name="Hemodialysis",
                    umls_cui="C0019004",
                    code_system="ICD10PCS",
                    primary_code="5A1D00Z",
                    confidence=0.90,
                    synonyms=["hemodialysis", "HD"]
                ),
            },
            
            "Demographic": {
                "age": StandardizedConcept(
                    original_text="age",
                    standard_name="Age",
                    umls_cui="C0001779",
                    code_system="SNOMED",
                    primary_code="397659008",
                    confidence=0.95
                ),
                "gender": StandardizedConcept(
                    original_text="gender",
                    standard_name="Gender",
                    umls_cui="C0079399",
                    code_system="SNOMED",
                    primary_code="263495000",
                    confidence=0.95,
                    synonyms=["sex"]
                ),
                "race": StandardizedConcept(
                    original_text="race",
                    standard_name="Race",
                    umls_cui="C0034510",
                    code_system="OMB",
                    primary_code="0",
                    confidence=0.95,
                    synonyms=["ethnicity"]
                ),
            },

            "Observation": {
                "imaging modality": StandardizedConcept(
                    original_text="imaging modality",
                    standard_name="Imaging modality",
                    umls_cui="C1881176",
                    code_system="SNOMED",
                    primary_code="363679005",
                    confidence=0.90,
                    synonyms=["imaging", "on any imaging modality"]
                ),
                "cardiac structural abnormalities": StandardizedConcept(
                    original_text="cardiac structural abnormalities",
                    standard_name="Cardiac structural abnormality",
                    umls_cui="C0018799",
                    code_system="SNOMED",
                    primary_code="128599005",
                    confidence=0.90,
                    synonyms=["objective evidence of cardiac structural abnormalities"]
                ),
                "cardiac functional abnormalities": StandardizedConcept(
                    original_text="cardiac functional abnormalities",
                    standard_name="Cardiac functional abnormality",
                    umls_cui="C0232164",
                    code_system="SNOMED",
                    primary_code="40443007",
                    confidence=0.90,
                    synonyms=["objective evidence of cardiac functional abnormalities"]
                ),
                "language ability": StandardizedConcept(
                    original_text="language ability",
                    standard_name="Ability to communicate",
                    umls_cui="C0870313",
                    code_system="SNOMED",
                    primary_code="288546006",
                    confidence=0.85,
                    synonyms=["ability to understand and speak"]
                ),
                "fasting": StandardizedConcept(
                    original_text="fasting",
                    standard_name="Fasting",
                    umls_cui="C0015663",
                    code_system="SNOMED",
                    primary_code="16985007",
                    confidence=0.95,
                    synonyms=["fasting conditions"]
                ),
            },

            "Value": {
                "dosage frequency": StandardizedConcept(
                    original_text="dosage frequency",
                    standard_name="Once daily",
                    umls_cui="C0556983",
                    code_system="UCUM",
                    primary_code="/d",
                    confidence=0.90,
                    synonyms=["once daily", "daily"]
                ),
            }
        }
        
        # Add normalized versions for case-insensitive lookup
        normalized_mappings = {}
        for domain, concepts in mappings.items():
            normalized_mappings[domain] = {}
            for key, concept in concepts.items():
                normalized_key = self._normalize_text(key)
                normalized_mappings[domain][normalized_key] = concept
                
                # Add synonym mappings
                for synonym in concept.synonyms:
                    synonym_key = self._normalize_text(synonym)
                    normalized_mappings[domain][synonym_key] = concept
        
        return normalized_mappings
    
    def _build_temporal_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build temporal pattern recognition mappings."""
        return {
            # Before patterns
            "before": {
                "patterns": [
                    r"before\s+(.+)",
                    r"prior\s+to\s+(.+)",
                    r"(.+)\s+before\s+(.+)",
                    r"within\s+(.+?)\s+before\s+(.+)",
                    r"(.+?)\s+prior\s+to\s+(.+)"
                ],
                "standard_pattern": "XBeforeY",
                "temporal_value_patterns": {
                    r"(\d+)\s*(day|days)": "P{}D",
                    r"(\d+)\s*(week|weeks)": "P{}W", 
                    r"(\d+)\s*(month|months)": "P{}M",
                    r"(\d+)\s*(year|years)": "P{}Y",
                    r"(\d+)\s*(hour|hours)": "PT{}H",
                    r"(\d+)\s*(minute|minutes)": "PT{}M"
                }
            },
            
            # After patterns
            "after": {
                "patterns": [
                    r"after\s+(.+)",
                    r"following\s+(.+)",
                    r"(.+)\s+after\s+(.+)",
                    r"within\s+(.+?)\s+after\s+(.+)",
                    r"(.+?)\s+following\s+(.+)"
                ],
                "standard_pattern": "XAfterY",
                "temporal_value_patterns": {
                    r"(\d+)\s*(day|days)": "P{}D",
                    r"(\d+)\s*(week|weeks)": "P{}W",
                    r"(\d+)\s*(month|months)": "P{}M", 
                    r"(\d+)\s*(year|years)": "P{}Y",
                    r"(\d+)\s*(hour|hours)": "PT{}H",
                    r"(\d+)\s*(minute|minutes)": "PT{}M"
                }
            },
            
            # During patterns
            "during": {
                "patterns": [
                    r"during\s+(.+)",
                    r"throughout\s+(.+)",
                    r"while\s+(.+)",
                    r"concurrent\s+with\s+(.+)"
                ],
                "standard_pattern": "XDuringY",
                "temporal_value_patterns": {}
            },
            
            # Within patterns
            "within": {
                "patterns": [
                    r"within\s+(.+)",
                    r"in\s+the\s+past\s+(.+)",
                    r"over\s+the\s+past\s+(.+)",
                    r"in\s+the\s+last\s+(.+)"
                ],
                "standard_pattern": "XWithinTime", 
                "temporal_value_patterns": {
                    r"(\d+)\s*(day|days)": "P{}D",
                    r"(\d+)\s*(week|weeks)": "P{}W",
                    r"(\d+)\s*(month|months)": "P{}M",
                    r"(\d+)\s*(year|years)": "P{}Y",
                    r"(\d+)\s*(hour|hours)": "PT{}H",
                    r"(\d+)\s*(minute|minutes)": "PT{}M"
                }
            }
        }
    
    def _build_domain_vocabularies(self) -> Dict[str, List[str]]:
        """Build preferred vocabularies by domain."""
        return {
            "Condition": ["SNOMED", "ICD10CM"],
            "Drug": ["RxNorm", "NDC"],
            "Measurement": ["LOINC", "SNOMED"],
            "Procedure": ["ICD10PCS", "CPT4", "SNOMED"],
            "Device": ["SNOMED", "NDC"],
            "Observation": ["SNOMED", "LOINC"],
            "Visit": ["CMS Place of Service", "SNOMED"],
            "Demographic": ["SNOMED", "OMB"],
            "Temporal": ["UCUM"],
            "Quantity": ["UCUM"],
            "Value": ["UCUM"]
        }
    
    def _build_abbreviation_map(self) -> Dict[str, str]:
        """Build common medical abbreviation mappings."""
        return {
            # Cardiovascular
            "mi": "myocardial infarction",
            "chf": "congestive heart failure", 
            "htn": "hypertension",
            "cvd": "cardiovascular disease",
            "cad": "coronary artery disease",
            "pci": "percutaneous coronary intervention",
            "cabg": "coronary artery bypass graft",
            
            # Measurements
            "bp": "blood pressure",
            "hr": "heart rate",
            "sbp": "systolic blood pressure", 
            "dbp": "diastolic blood pressure",
            "hgb": "hemoglobin",
            "hb": "hemoglobin",
            "wbc": "white blood cell",
            "rbc": "red blood cell",
            
            # Conditions
            "dm": "diabetes mellitus",
            "copd": "chronic obstructive pulmonary disease",
            "uti": "urinary tract infection",
            "tbi": "traumatic brain injury",
            "cva": "cerebrovascular accident",
            "ckd": "chronic kidney disease",
            
            # Drugs
            "asa": "aspirin",
            "ace": "angiotensin converting enzyme",
            "arb": "angiotensin receptor blocker",
            
            # Time units
            "yrs": "years",
            "yr": "year", 
            "mos": "months",
            "mo": "month",
            "wks": "weeks",
            "wk": "week",
            "hrs": "hours",
            "hr": "hour",
            "mins": "minutes",
            "min": "minute"
        }
    
    def standardize_entity(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """
        Standardize a single entity using offline mappings.
        
        Args:
            entity: Entity to standardize
            
        Returns:
            Enhanced entity with standardization information
        """
        # Expand abbreviations first
        expanded_text = self._expand_abbreviations(entity.text)
        normalized_text = self._normalize_text(expanded_text)
        
        # Try exact match first
        concept = self._exact_match(normalized_text, entity.domain)
        
        # Try fuzzy match if no exact match
        if not concept:
            concept = self._fuzzy_match(normalized_text, entity.domain)
        
        # Apply standardization if found
        if concept:
            return self._apply_standardization(entity, concept)
        else:
            # Return original entity with minimal standardization
            return self._apply_minimal_standardization(entity, expanded_text)
    
    def standardize_temporal_relation(self, text: str) -> Optional[TemporalRelation]:
        """
        Standardize temporal expressions.
        
        Args:
            text: Text containing temporal relationship
            
        Returns:
            Standardized temporal relation or None if not found
        """
        text_lower = text.lower()
        
        for pattern_type, pattern_info in self.temporal_patterns.items():
            for pattern in pattern_info["patterns"]:
                match = re.search(pattern, text_lower)
                if match:
                    # Extract temporal value if present
                    temporal_value = self._extract_temporal_value(
                        text_lower, pattern_info["temporal_value_patterns"]
                    )
                    
                    return TemporalRelation(
                        pattern=pattern_info["standard_pattern"],
                        value=text,
                        normalized_duration=temporal_value,
                        subject_concept=match.groups()[0] if len(match.groups()) > 0 else None,
                        reference_concept=match.groups()[1] if len(match.groups()) > 1 else None,
                        confidence=0.8
                    )
        
        return None
    
    def _exact_match(self, normalized_text: str, domain: str) -> Optional[StandardizedConcept]:
        """Find exact match in concept mappings."""
        domain_mappings = self.concept_mappings.get(domain, {})
        return domain_mappings.get(normalized_text)
    
    def _fuzzy_match(self, normalized_text: str, domain: str, threshold: float = 0.8) -> Optional[StandardizedConcept]:
        """Find fuzzy match in concept mappings."""
        domain_mappings = self.concept_mappings.get(domain, {})
        
        best_match = None
        best_score = 0.0
        
        for concept_key, concept in domain_mappings.items():
            similarity = self._calculate_similarity(normalized_text, concept_key)
            if similarity > threshold and similarity > best_score:
                best_match = concept
                best_score = similarity
        
        return best_match
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity score."""
        # Use SequenceMatcher for basic similarity
        seq_similarity = SequenceMatcher(None, text1, text2).ratio()
        
        # Word-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if words1 and words2:
            word_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
            return max(seq_similarity, word_similarity)
        
        return seq_similarity
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Remove punctuation and extra whitespace
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _expand_abbreviations(self, text: str) -> str:
        """Expand common medical abbreviations."""
        words = text.split()
        expanded_words = []
        
        for word in words:
            word_lower = word.lower().rstrip('.,;:')
            if word_lower in self.abbreviation_map:
                expanded_words.append(self.abbreviation_map[word_lower])
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words)
    
    def _extract_temporal_value(self, text: str, value_patterns: Dict[str, str]) -> Optional[str]:
        """Extract and normalize temporal values."""
        for pattern, template in value_patterns.items():
            match = re.search(pattern, text)
            if match:
                number = match.group(1)
                return template.format(number)
        return None
    
    def _apply_standardization(self, entity: EnhancedNamedEntity, concept: StandardizedConcept) -> EnhancedNamedEntity:
        """Apply standardization information to entity."""
        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=entity.confidence,
            # Standardization fields
            standard_name=concept.standard_name,
            umls_cui=concept.umls_cui,
            code_system=concept.code_system,
            code_set=[concept.primary_code] if concept.primary_code else None,
            primary_code=concept.primary_code,
            metadata={
                **(entity.metadata or {}),
                'standardization': {
                    'method': 'offline_exact',
                    'confidence': concept.confidence,
                    'synonyms': concept.synonyms,
                    'original_text': entity.text,
                    'expanded_text': concept.original_text
                }
            }
        )
    
    def _apply_minimal_standardization(self, entity: EnhancedNamedEntity, expanded_text: str) -> EnhancedNamedEntity:
        """Apply minimal standardization when no match found - returns entity without codes."""
        # Generate simple standardized name only
        standard_name = expanded_text.title()

        # DO NOT generate placeholder codes - leave empty for Stage 3 to handle
        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=entity.confidence,
            # Minimal standardization - no codes, just normalized text
            standard_name=standard_name,
            umls_cui=None,  # Stage 3 will fill this via UMLS/OHDSI
            code_system=None,  # Stage 3 will fill this
            code_set=None,
            primary_code=None,
            metadata={
                **(entity.metadata or {}),
                'standardization': {
                    'method': 'offline_skip',
                    'confidence': 0.0,  # No standardization applied
                    'original_text': entity.text,
                    'expanded_text': expanded_text,
                    'note': 'No match in offline vocabulary - will be processed in Stage 3 (CDM Mapping)'
                }
            }
        )


__all__ = ["OfflineStandardizer", "StandardizedConcept"]