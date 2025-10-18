# Requirements Files Comparison

## Overview

This project now has a comprehensive `requirements.txt` that consolidates all backend dependencies.

## Files

### 1. [requirements.txt](./requirements.txt) ⭐ **PRIMARY FILE**
- **Purpose**: Complete backend dependencies with all features
- **Packages**: 35 total
- **Status**: Current, recommended for all installations
- **Use case**: All backend development and production deployments

### 2. [requirements-api.txt](./requirements-api.txt) 📦 **LEGACY**
- **Purpose**: Original API-focused dependencies
- **Packages**: ~30 total
- **Status**: Legacy, kept for reference
- **Use case**: Historical reference only

## Key Differences

### Added in `requirements.txt`
1. **filelock** (≥3.12.0) - Used in cache management
2. **tenacity** (≥8.2.0) - Retry logic for API calls
3. **pytest-asyncio** (≥0.21.0) - Async test support
4. **numpy** (≥1.24.0) - Explicitly specified (was implicit dependency)

### Enhanced Documentation
- Comprehensive inline comments
- Categorized by functionality
- Version rationale explained
- Optional packages clearly marked

## Migration Guide

### For Existing Installations

```bash
# Option 1: Update existing environment
pip install -r backend/requirements.txt

# Option 2: Fresh installation (recommended)
python -m venv venv_new
source venv_new/bin/activate
pip install -r backend/requirements.txt
```

### For New Projects

```bash
# Only use requirements.txt
pip install -r backend/requirements.txt
```

## Package Count by Category

| Category | Packages | % of Total |
|----------|----------|------------|
| Web Framework | 5 | 14% |
| Data Processing | 3 | 9% |
| Statistical Analysis | 6 | 17% |
| Visualization | 2 | 6% |
| LangChain & AI | 5 | 14% |
| LLM Clients | 3 | 9% |
| API & HTTP | 2 | 6% |
| Utilities | 5 | 14% |
| Testing | 4 | 11% |
| **Total** | **35** | **100%** |

## Verification

```bash
# Verify all packages are installed correctly
./venv/bin/python backend/verify_deps.py
```

Expected output:
```
✅ All dependencies verified successfully!
🚀 Backend is ready to run!
```

## Related Documentation

- [INSTALLATION.md](./INSTALLATION.md) - Detailed installation guide
- [DEPENDENCIES_SUMMARY.md](./DEPENDENCIES_SUMMARY.md) - Package overview
- [verify_deps.py](./verify_deps.py) - Verification script

## Recommendations

1. ✅ **Use `requirements.txt`** for all new installations
2. 📦 Keep `requirements-api.txt` for historical reference
3. 🔍 Run `verify_deps.py` after installation
4. 📝 Document any additional dependencies added to project
5. 🔄 Periodically update packages with `pip list --outdated`

## Future Considerations

### Potential Additions
- **ruff** - Fast Python linter/formatter
- **pyright** - Static type checker
- **ipython** - Enhanced Python shell
- **jupyter** - Notebook support

### Production Hardening
- Pin exact versions in `requirements-frozen.txt`
- Use `pip-compile` for dependency resolution
- Add security scanning with `safety check`
