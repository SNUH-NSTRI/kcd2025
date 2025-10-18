# Backend Installation Guide

## Prerequisites

- Python 3.9 or higher (tested with Python 3.13)
- pip or uv package manager
- Virtual environment (recommended)

## Quick Start

### 1. Create Virtual Environment (if not exists)

```bash
# From project root
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install all backend dependencies
pip install -r backend/requirements.txt

# Or with specific Python path
./venv/bin/python -m pip install -r backend/requirements.txt
```

### 3. Verify Installation

```bash
./venv/bin/python -c "
import fastapi, pandas, numpy, scipy, econml, lifelines
import langchain, langgraph, sklearn, shap, openai
print('✓ All critical packages installed successfully')
"
```

## Environment Setup

Create a `.env` file in the `backend/` directory:

```bash
# Backend Environment Variables
WORKSPACE_ROOT=./workspace
CORS_ORIGINS=http://localhost:3000

# OpenRouter API (for LLM services)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: Redis cache
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional: UMLS API
UMLS_API_KEY=your_umls_api_key_here
```

## Running the Backend

### Development Server

```bash
# From project root
npm run backend

# Or directly with uvicorn
./venv/bin/python -m uvicorn backend.src.rwe_api.main:app --reload --port 8000
```

### Production Server

```bash
./venv/bin/python -m uvicorn backend.src.rwe_api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Testing

```bash
# Run all tests
./venv/bin/python -m pytest backend/tests -v

# Run with coverage
./venv/bin/python -m pytest backend/tests --cov=backend/src --cov-report=html

# Run specific test file
./venv/bin/python -m pytest backend/tests/test_agents.py -v
```

## Package Overview

### Core Framework (5 packages)
- **fastapi** (0.115.0) - Modern web framework
- **uvicorn** (0.32.0) - ASGI server
- **pydantic** (2.9.2) - Data validation
- **pydantic-settings** (2.11.0) - Settings management
- **python-multipart** (0.0.12) - Form data parsing

### Data Processing (3 packages)
- **pandas** (≥2.0.0) - Data manipulation
- **pyarrow** (≥14.0.0) - Columnar data format
- **numpy** (≥1.24.0) - Numerical computing

### Statistical Analysis (6 packages)
- **lifelines** (≥0.29.0) - Survival analysis (Cox, Kaplan-Meier)
- **econml** (≥0.15.0) - Causal inference (Causal Forest, HTE)
- **shap** (≥0.45.0) - Feature importance (Shapley values)
- **scikit-learn** (≥1.3.0) - Machine learning (PSM, regression)
- **statsmodels** (≥0.14.0) - Statistical tests
- **scipy** (≥1.11.0) - Scientific computing

### Visualization (2 packages)
- **matplotlib** (≥3.7.0) - Plotting library
- **seaborn** (≥0.12.0) - Statistical visualizations

### LangChain & AI Agents (5 packages)
- **langchain** (≥0.1.0) - LLM orchestration framework
- **langchain-core** (≥0.1.0) - Core abstractions
- **langchain-openai** (≥0.0.5) - OpenRouter integration
- **langchain-text-splitters** (≥0.3.0) - Text processing
- **langgraph** (≥0.0.20) - Graph-based workflows

### LLM Clients (3 packages)
- **openai** (≥2.0.0) - OpenAI/OpenRouter API
- **httpx** (≥0.28.0) - Async HTTP client
- **tiktoken** (≥0.12.0) - Tokenization

### API & HTTP (2 packages)
- **requests** (≥2.31.0) - HTTP client
- **urllib3** (≥2.0.0) - HTTP library

### Utilities (4 packages)
- **redis** (≥5.0.0) - Caching (optional)
- **filelock** (≥3.12.0) - File locking
- **tenacity** (≥8.2.0) - Retry logic
- **python-dotenv** (1.0.1) - Environment variables
- **pyyaml** (≥6.0.1) - YAML parsing

### Testing (4 packages)
- **pytest** (≥7.4.0) - Testing framework
- **pytest-cov** (≥4.1.0) - Coverage reporting
- **pytest-mock** (≥3.12.0) - Mocking support
- **pytest-asyncio** (≥0.21.0) - Async testing

## Troubleshooting

### Common Issues

1. **Import errors after installation**
   - Ensure you're using the correct Python interpreter: `which python`
   - Activate virtual environment: `source venv/bin/activate`

2. **OpenRouter API errors**
   - Verify `OPENROUTER_API_KEY` is set in `.env`
   - Check API key validity at https://openrouter.ai

3. **Permission errors**
   - Ensure write permissions for `./workspace` directory
   - Check file lock permissions in cache directories

4. **Memory errors during analysis**
   - Reduce cohort size for testing
   - Use `load_cohort_sample()` for large datasets
   - Increase system swap space

### Dependency Conflicts

If you encounter version conflicts:

```bash
# Clear pip cache
pip cache purge

# Reinstall with specific versions
pip install --force-reinstall -r backend/requirements.txt

# Or use isolated environment
python -m venv venv_fresh
source venv_fresh/bin/activate
pip install -r backend/requirements.txt
```

## Updating Dependencies

```bash
# Update all packages to latest compatible versions
pip install --upgrade -r backend/requirements.txt

# Update specific package
pip install --upgrade fastapi

# Generate new requirements file with exact versions
pip freeze > backend/requirements-frozen.txt
```

## Development Tools (Optional)

For enhanced development experience:

```bash
# Code formatting & linting
pip install ruff

# Type checking
pip install pyright

# Interactive shell
pip install ipython

# Notebook support
pip install jupyter
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Pandas Documentation](https://pandas.pydata.org/)
- [Scikit-learn Documentation](https://scikit-learn.org/)
- [EconML Documentation](https://econml.azurewebsites.net/)
- [Lifelines Documentation](https://lifelines.readthedocs.io/)

## Support

For issues or questions:
- Check project documentation in `/vooster-docs`
- Review API examples in `./API_SEARCH_LIT.md`
- Consult feature guides in `./FEATURE_TYPES_GUIDE.md`
