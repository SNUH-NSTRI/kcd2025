# 🏥 Agentic RWE Clinical Trial Emulation Platform

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/Node.js-18.0%2B-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Korea Clinical Datathon 2025 - Team H**
>
> *Agentic Trial Emulation Real-World Evidence 생성 자동화 파이프라인 구축 연구*

---


## 📖 Overview

An **AI-powered multi-agent system** for automated clinical trial emulation using real-world evidence (RWE). This platform transforms the entire workflow from evidence retrieval to comprehensive report generation through intelligent automation and microservices architecture.

### 🎯 Core Objectives

Development of a multi-agent system for clinical trial emulation, encompassing the entire workflow from evidence retrieval to report generation through four integrated modules:

#### 1. 🔍 Clinical Trial Intelligence

Automated search and structured extraction of eligibility criteria and study parameters from public trial databases (e.g., [ClinicalTrials.gov](http://clinicaltrials.gov/))

#### 2. 💾 Real-World Data Mapping

Mapping inclusion/exclusion criteria and treatment definitions to real-world EHR data within the MIMIC-IV database for cohort construction

#### 3. 📊 Statistical Analysis Engine

Execution of emulated trial analyses using appropriate statistical models:

- Cox regression for survival analysis
- Inverse Probability of Treatment Weighting (IPTW)
- Propensity score matching
- Causal inference frameworks

#### 4. 📄 Intelligent Reporting

Generation of structured summaries and visual reports integrating:

- Extracted trial data
- Statistical results and visualizations
- Comparisons with original trial outcomes
- Supporting literature from PubMed Central

### ✨ Key Features

- 🤖 **Multi-Agent Architecture** - Specialized agents (Trialist, Statistician) for each workflow stage
- 🔄 **7-Stage Pipeline** - Systematic processing from data ingestion to report generation
- 📈 **Advanced Analytics** - Causal inference, survival analysis, and treatment effect estimation
- 🎨 **Interactive UI** - Modern React-based interface with real-time streaming reports
- 🔗 **Microservices Design** - Scalable FastAPI backend with Next.js frontend
- 📚 **LLM Integration** - LangChain/LangGraph powered intelligent processing
- 📖 **Literature Integration** - Automatic fetching and incorporation of NCT trial papers

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

| Requirement       | Version | Purpose            |
| ----------------- | ------- | ------------------ |
| **Python**  | 3.9+    | Backend runtime    |
| **Node.js** | 18.0+   | Frontend runtime   |
| **npm**     | 9.0+    | Package management |
| **Git**     | Latest  | Version control    |

---

## 🚀 Quick Start

### 1️⃣ Clone the Repository

```bash
git clone <repository-url>
cd datathon_public
```

### 2️⃣ Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create and configure .env file
cp .env.example .env
# Edit .env with your API keys:
# - OPENROUTER_API_KEY=your_key_here
# - WORKSPACE_ROOT=./workspace
# - CORS_ORIGINS=http://localhost:3000

# Run backend server (port 8000)
uvicorn rwe_api.main:app --reload
```

**Backend will be available at:** `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs`

### 3️⃣ Frontend Setup

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install dependencies
npm install

# Create and configure .env.local file
cp .env.example .env.local
# Edit .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server (port 3000)
npm run dev
```

**Frontend will be available at:** `http://localhost:3000`

### 4️⃣ Run Both Services Simultaneously

```bash
# From project root directory
npm run dev:all
```

---

## 🏗️ Project Architecture

```text
datathon_public/
├── backend/                 # FastAPI microservice
│   ├── src/
│   │   ├── agents/          # AI agents
│   │   │   ├── statistician/     # Statistical analysis agent
│   │   │   └── trialist_hybrid/  # Trial extraction agent
│   │   ├── pipeline/        # 7-stage pipeline implementation
│   │   │   ├── plugins/          # Pipeline plugins
│   │   │   └── stages/           # Individual pipeline stages
│   │   └── rwe_api/         # API routes and schemas
│   │       ├── routes/           # REST API endpoints
│   │       └── schemas/          # Pydantic models
│   ├── tests/               # Backend test suite
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment template
│
├── frontend/                # Next.js application
│   ├── src/
│   │   ├── app/             # Next.js 15 App Router
│   │   │   ├── (app)/           # Main application routes
│   │   │   └── layout.tsx       # Root layout
│   │   ├── features/        # Feature modules
│   │   │   ├── analysis/        # Statistical analysis UI
│   │   │   ├── report/          # Report generation UI
│   │   │   └── schema/          # Schema mapping UI
│   │   ├── components/      # Shared UI components
│   │   └── remote/          # API client layer
│   ├── package.json         # Node dependencies
│   └── .env.example         # Environment template
│
├── scripts/                 # Utility scripts
├── project/                 # Project data storage
│   └── NCT*/                # Trial-specific workspaces
└── workspace/               # Runtime data directory
```

### 🔄 System Workflow

```mermaid
graph TD
    A[NCT ID Input] --> B[Trial Agent]
    B --> C[Information Agent]
    C --> D[Eligibility Mapping]
    C --> E[MIMIC-IV Cohort Construction]
    D --> E
    E --> F[Statistics Agent]
    F --> G[Report Agent]
    G --> H[Interactive Results]

    style C fill:#e1f5ff,stroke:#0288d1,stroke-width:3px
    style D fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style E fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
```

---

## 📦 Technology Stack

### Backend

- **Web Framework:** FastAPI 0.104+, Uvicorn, Pydantic
- **Data Processing:** Pandas, NumPy, PyArrow
- **Statistical Analysis:**
  - Lifelines (survival analysis)
  - EconML (causal inference)
  - SHAP (explainability)
  - Scikit-learn, Statsmodels
- **Visualization:** Matplotlib, Seaborn
- **LLM Integration:** LangChain, LangGraph, OpenAI
- **Testing:** pytest, pytest-cov, pytest-asyncio

### Frontend

- **Framework:** Next.js 15, React 19, TypeScript 5
- **UI Components:** Radix UI, Tailwind CSS, shadcn/ui
- **State Management:** Zustand, TanStack Query (React Query)
- **Forms:** React Hook Form, Zod validation
- **Icons:** Lucide React
- **Charts:** Recharts, D3.js

---

## 🔧 Development

### Backend Commands

```bash
# Run all tests
pytest backend/tests -v

# Run specific test file
pytest backend/tests/test_agents.py -v

# Run specific test function
pytest backend/tests/test_file.py::test_function -v

# Run with coverage report
pytest backend/tests --cov=src --cov-report=html

# Format code (if ruff installed)
ruff format backend/src

# Lint code
ruff check backend/src

# Type check
pyright backend/src
```

### Frontend Commands

```bash
# Build for production
npm run build

# Run linter
npm run lint

# Type check
npm run type-check

# Start production server
npm run start

# Clean build artifacts
npm run clean
```

---

## 🔑 Environment Configuration

### Backend (.env)

```env
# Workspace configuration
WORKSPACE_ROOT=./workspace

# CORS settings
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# LLM API configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: Database configuration
# DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Optional: Logging
# LOG_LEVEL=INFO
```

### Frontend (.env.local)

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Analytics
# NEXT_PUBLIC_GA_ID=your_google_analytics_id
```

---

## 📚 API Endpoints

### Core Endpoints

| Method   | Endpoint                     | Description                  |
| -------- | ---------------------------- | ---------------------------- |
| `GET`  | `/health`                  | Health check                 |
| `POST` | `/agents/trialist/run`     | Run trial extraction agent   |
| `POST` | `/agents/statistician/run` | Run statistical analysis     |
| `GET`  | `/agents/status/{run_id}`  | Check agent status           |
| `POST` | `/eligibility/extract`     | Extract eligibility criteria |
| `GET`  | `/projects/{nct_id}`       | Get project details          |

**Full API documentation:** `http://localhost:8000/docs` (Swagger UI)

---

## 🧪 Testing

### Backend Tests

```bash
# Run all tests
cd backend
pytest tests -v

# Run with coverage
pytest tests --cov=src --cov-report=term-missing

# Run specific test suite
pytest tests/test_agents/ -v
```

### Frontend Tests

```bash
# Run frontend tests (if configured)
cd frontend
npm test

# Run in watch mode
npm test -- --watch
```

---

## 📖 Documentation

- **[Backend Installation Guide](backend/INSTALLATION.md)** - Detailed backend setup instructions
- **[Backend Agents README](backend/AGENTS_README.md)** - Agent architecture and usage
- **[Dependencies Summary](backend/DEPENDENCIES_SUMMARY.md)** - Package dependencies explanation
- **[Requirements Comparison](backend/REQUIREMENTS_COMPARISON.md)** - Dependency version analysis

---

## 🚨 Troubleshooting

### Common Issues

#### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.9+

# Verify virtual environment is activated
which python  # Should point to venv/bin/python

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

#### Frontend build errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Next.js cache
rm -rf .next
npm run build
```

#### Port conflicts

```bash
# Check if ports are in use
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Kill processes if needed
kill -9 <PID>
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create your feature branch**

   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. **Commit your changes**

   ```bash
   git commit -m 'Add some AmazingFeature'
   ```
4. **Push to the branch**

   ```bash
   git push origin feature/AmazingFeature
   ```
5. **Open a Pull Request**

### Development Guidelines

- Follow existing code style
- Add tests for new features
- Update documentation as needed
- Keep commits atomic and well-described

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

**Korea Clinical Datathon 2025 - Team H**

---

## 📧 Support

For issues, questions, or feature requests:

- **GitHub Issues:** [https://github.com/](https://github.com/your-repo/issues)
- **Email:** yeonghyeon.kim@snu.ac.kr

---

## 🙏 Acknowledgments

- MIMIC-IV database by MIT LCP
- ClinicalTrials.gov for trial data
- PubMed Central for literature access
- OpenRouter for LLM API access

---

## 👥 Contributors

* [ ] This project was developed through an open, cross-institutional collaboration among researchers specializing in **bioengineering, medical informatics, anesthesiology, pathology, and computational medicine**.
  Each contributor played a central role in the development, validation, and conceptualization of the **Agentic Trial Emulation Framework**.

| Name                     | Affiliation                                                                                                          | Role / Contribution                                                             |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Yeonghyeon Kim** | Interdisciplinary Program in Bioengineering, Seoul National University (BiLab, Prof. Dongheon Lee)                   | **Team Lead** · Agent architecture and framework development             |
| **Jiho Kim**       | Department of Medical Informatics, College of Medicine, The Catholic University of Korea (BIDA Lab, Prof. Taehun Ko) | **Trial Agent** · Development and validation                             |
| **YunWook Sung**   | Department of Anesthesiology and Pain Medicine, Seoul National University Hospital (VitalLab, Prof. Hyungchul Lee)   | **Trial Agent** · Development and validation                             |
| **Minkook Son**    | Department of Physiology, College of Medicine, Dong-A University (PILLab)                                            | **Information Agent** · Development, validation, and idea contribution   |
| **Eunjoo Shin**    | Department of Anesthesiology and Pain Medicine, Seoul National University Hospital (VitalLab, Prof. Hyungchul Lee)   | **Trial Agent** · Development, validation, and presentation design       |
| **Sangjeong Ahn**  | Department of Pathology, Korea University College of Medicine (PathFinder Lab)                                       | **Exploratory Data Analysis** · Visualization and presentation materials |
| **Hanjoo Lee**     | Seoul National University Hospital, Medical Vision Lab (Prof. Younggon Kim)                                          | **Statistics Agent** · Development, validation, and exploratory analysis |
| **Seunghoon Jo**   | Graduate School of Medical Science and Engineering, UNIST (ICBM Lab, Prof. Minhyeok Lim)                             | **Information Agent** · Development, validation, and data analysis       |

> _All contributors participated actively in model design, implementation, and validation phases.
> The project reflects shared authorship, equal contribution, and a collective commitment to open, reproducible medical AI research._

---

### 🌱 Open Collaboration Philosophy

This repository embodies our belief that **transparency, reproducibility, and shared authorship** are essential in advancing medical AI research.We welcome collaborations, critiques, and extensions through open discussions and pull requests.

> “Science progresses fastest when built in public — reproducible, inspectable, and improvable by anyone.”

**Last Updated:** October 2025

**Version:** 1.0.0
