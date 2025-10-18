# Backend Dependencies Summary

## 📦 Total Packages: 35

Generated on: 2025-10-18
Python Version: 3.9+

## Package Categories

### 🌐 Web Framework (5 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.115.0 | Modern async web framework |
| uvicorn[standard] | 0.32.0 | ASGI server with WebSocket support |
| pydantic | 2.9.2 | Data validation using Python type annotations |
| pydantic-settings | 2.11.0 | Settings management from environment |
| python-multipart | 0.0.12 | Multipart form data parsing |

### 📊 Data Processing (3 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| pandas | ≥2.0.0 | Data manipulation and analysis |
| pyarrow | ≥14.0.0 | Columnar memory format for analytics |
| numpy | ≥1.24.0 | Numerical computing fundamentals |

### 📈 Statistical Analysis (6 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| lifelines | ≥0.29.0 | Survival analysis (Cox PH, Kaplan-Meier) |
| econml | ≥0.15.0 | Causal inference (Causal Forest, HTE) |
| shap | ≥0.45.0 | Model explainability (Shapley values) |
| scikit-learn | ≥1.3.0 | Machine learning (PSM, classification) |
| statsmodels | ≥0.14.0 | Statistical modeling and tests |
| scipy | ≥1.11.0 | Scientific computing library |

### 📉 Visualization (2 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| matplotlib | ≥3.7.0 | Publication-quality plots |
| seaborn | ≥0.12.0 | Statistical data visualization |

### 🤖 LangChain & AI (5 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| langchain | ≥0.1.0 | LLM application framework |
| langchain-core | ≥0.1.0 | Core LangChain abstractions |
| langchain-openai | ≥0.0.5 | OpenRouter/OpenAI integration |
| langchain-text-splitters | ≥0.3.0 | Text chunking utilities |
| langgraph | ≥0.0.20 | Graph-based agent workflows |

### 🧠 LLM Clients (3 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| openai | ≥2.0.0 | OpenAI/OpenRouter API client |
| httpx | ≥0.28.0 | Modern async HTTP client |
| tiktoken | ≥0.12.0 | OpenAI tokenization library |

### 🌍 API & HTTP (2 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| requests | ≥2.31.0 | HTTP library for API calls |
| urllib3 | ≥2.0.0 | HTTP client library |

### 🔧 Utilities (4 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| redis | ≥5.0.0 | In-memory caching (optional) |
| filelock | ≥3.12.0 | Cross-platform file locking |
| tenacity | ≥8.2.0 | Retry logic with backoff |
| python-dotenv | 1.0.1 | .env file management |
| pyyaml | ≥6.0.1 | YAML configuration parsing |

### 🧪 Testing (4 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | ≥7.4.0 | Testing framework |
| pytest-cov | ≥4.1.0 | Coverage reporting |
| pytest-mock | ≥3.12.0 | Mocking utilities |
| pytest-asyncio | ≥0.21.0 | Async test support |

## 🎯 Key Features Enabled

### Clinical Trial Emulation
- **Literature Search**: LangChain + OpenRouter for trial discovery
- **Trial Parsing**: LangGraph agents for NER + standardization
- **EHR Mapping**: UMLS/OHDSI clients for medical vocabulary
- **Cohort Filtering**: Pandas + NumPy for data processing

### Statistical Analysis
- **Propensity Score Matching**: scikit-learn + custom PSM
- **Survival Analysis**: lifelines (Cox PH, Kaplan-Meier)
- **Causal Inference**: econml (Causal Forest, Double ML)
- **Feature Importance**: SHAP for model explainability

### Agent Workflows
- **Statistician Agent**: Multi-method RCT emulation
- **Trialist Parser**: 4-stage trial criteria extraction
- **Report Generator**: Comprehensive analysis reports
- **Cache Management**: Redis + filelock for performance

## 📥 Installation

```bash
# Standard installation
pip install -r backend/requirements.txt

# With virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r backend/requirements.txt

# Verify installation
python -c "import fastapi, pandas, econml, langchain; print('✓ OK')"
```

## 🔍 Verification Script

```python
#!/usr/bin/env python3
"""Verify all critical dependencies are installed."""

import sys

REQUIRED_PACKAGES = [
    ('fastapi', 'FastAPI'),
    ('pandas', 'Pandas'),
    ('numpy', 'NumPy'),
    ('scipy', 'SciPy'),
    ('econml', 'EconML'),
    ('lifelines', 'Lifelines'),
    ('langchain', 'LangChain'),
    ('langgraph', 'LangGraph'),
    ('sklearn', 'Scikit-learn'),
    ('shap', 'SHAP'),
    ('openai', 'OpenAI'),
]

print('🔍 Verifying backend dependencies...\n')

missing = []
for module_name, display_name in REQUIRED_PACKAGES:
    try:
        module = __import__(module_name)
        version = getattr(module, '__version__', 'unknown')
        print(f'✓ {display_name:15} {version}')
    except ImportError:
        print(f'✗ {display_name:15} NOT INSTALLED')
        missing.append(display_name)

if missing:
    print(f'\n❌ Missing packages: {", ".join(missing)}')
    sys.exit(1)
else:
    print('\n✅ All dependencies verified successfully!')
    sys.exit(0)
```

Save as `backend/verify_deps.py` and run:
```bash
./venv/bin/python backend/verify_deps.py
```

## 📋 Related Files

- [requirements.txt](./requirements.txt) - Full dependency list
- [INSTALLATION.md](./INSTALLATION.md) - Detailed installation guide
- [requirements-api.txt](./requirements-api.txt) - Original API dependencies (legacy)

## 🔄 Update History

- **2025-10-18**: Complete requirements.txt created
  - Added missing dependencies: filelock, tenacity, pytest-asyncio
  - Organized into logical categories
  - Added comprehensive documentation
