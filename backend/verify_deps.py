#!/usr/bin/env python3
"""
Verify all critical backend dependencies are installed.

Usage:
    ./venv/bin/python backend/verify_deps.py
"""

import sys

REQUIRED_PACKAGES = [
    ('fastapi', 'FastAPI'),
    ('uvicorn', 'Uvicorn'),
    ('pydantic', 'Pydantic'),
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
    ('requests', 'Requests'),
    ('filelock', 'FileLock'),
    ('tenacity', 'Tenacity'),
    ('pytest', 'Pytest'),
]

def main():
    print('🔍 Verifying backend dependencies...')
    print('=' * 60)
    print()

    missing = []
    installed = []

    for module_name, display_name in REQUIRED_PACKAGES:
        try:
            module = __import__(module_name)
            version = getattr(module, '__version__', 'unknown')
            print(f'✓ {display_name:20} {version}')
            installed.append(display_name)
        except ImportError:
            print(f'✗ {display_name:20} NOT INSTALLED')
            missing.append(display_name)

    print()
    print('=' * 60)
    print(f'📊 Summary: {len(installed)}/{len(REQUIRED_PACKAGES)} packages installed')
    print()

    if missing:
        print(f'❌ Missing packages ({len(missing)}):')
        for pkg in missing:
            print(f'   - {pkg}')
        print()
        print('💡 Install missing packages:')
        print('   pip install -r backend/requirements.txt')
        sys.exit(1)
    else:
        print('✅ All dependencies verified successfully!')
        print('🚀 Backend is ready to run!')
        sys.exit(0)

if __name__ == '__main__':
    main()
