# Multi-Agent System

The RWE Clinical Trial Emulation Platform includes a multi-agent system for automated analytical workflows. Agents are intelligent, autonomous modules that can analyze data, make recommendations, and generate reports using LLM-powered decision making.

## Architecture

### Core Components

```
backend/src/
├── agents/
│   ├── base.py              # BaseAgent abstract class
│   ├── __init__.py          # Agent registry system
│   └── statistician/        # Statistician Agent package
│       ├── agent.py         # BaseAgent implementation
│       ├── graph.py         # LangGraph workflow (4 nodes)
│       ├── utils.py         # Path & validation utilities
│       ├── workflow.py      # PSMSurvivalWorkflow
│       └── analysis/        # Statistical analysis modules
└── rwe_api/
    ├── routes/agents.py     # FastAPI endpoints
    └── schemas/agents.py    # Pydantic models
```

### Agent Registry

All agents are registered through a decorator pattern:

```python
from agents import register_agent, get_agent, list_agents

# Get an agent
agent = get_agent("statistician")

# List all agents
agents = list_agents()
# [{"name": "statistician", "version": "0.1.0", "description": "..."}]
```

## Available Agents

### 1. Statistician Agent

Automated PSM (Propensity Score Matching) + Survival Analysis with LLM-powered parameter recommendation.

**Version:** 0.1.0
**Status:** Production-ready

#### What it does

1. **Analyzes baseline data** - Calculates cohort statistics, SMD, missingness
2. **Recommends PSM parameters** - LLM (GPT-4o-mini) suggests optimal caliper, matching ratio, variable selection
3. **Executes PSM + Survival Analysis** - Runs matching, balance assessment, Cox regression, Kaplan-Meier
4. **Interprets results** - LLM generates plain-language clinical interpretation

#### Workflow (LangGraph)

```mermaid
graph LR
    A[Analyze Baseline] --> B[Recommend Params]
    B --> C[Execute PSM]
    C --> D[Interpret Results]
```

**4 Nodes:**
- `analyze_baseline_node`: Load cohort, calculate SMD, assess missingness
- `recommend_psm_params_node`: LLM recommends optimal PSM parameters
- `execute_psm_workflow_node`: Run PSM + Survival Analysis
- `interpret_results_node`: LLM interprets results, generates report

#### Usage

**Backend (Python):**

```python
from agents import get_agent

agent = get_agent("statistician")

# Validate inputs
is_valid, error = await agent.validate_inputs(
    nct_id="NCT03389555",
    medication="hydrocortisone na succ.",
    openrouter_api_key="your-key",
    workspace_root="/path/to/workspace"
)

if not is_valid:
    print(f"Validation failed: {error}")
    return

# Run agent
result = await agent.run(
    nct_id="NCT03389555",
    medication="hydrocortisone na succ.",
    openrouter_api_key="your-key"
)

if result.success:
    print(f"✅ Analysis complete")
    print(f"Interpretation: {result.output['interpretation']}")
else:
    print(f"❌ Failed: {result.error}")
```

**Frontend (TypeScript):**

```typescript
import { agentsApi, AgentStatus } from "@/remote";

// Start agent execution
const response = await agentsApi.runStatistician(
  "NCT03389555",
  "hydrocortisone na succ."
);

const jobId = response.data.job_id;

// Poll for completion
const interval = setInterval(async () => {
  const status = await agentsApi.pollJobStatus(jobId);

  if (status.data.status === AgentStatus.COMPLETED) {
    console.log("✅ Agent completed:", status.data.result);
    clearInterval(interval);
  } else if (status.data.status === AgentStatus.FAILED) {
    console.error("❌ Agent failed:", status.data.error);
    clearInterval(interval);
  } else {
    console.log("⏳ Progress:", status.data.progress);
  }
}, 2000);
```

#### Required Environment

- **OPENROUTER_API_KEY**: API key for GPT-4o-mini access
- **Cohort file must exist**: `project/{NCT_ID}/cohorts/{medication}/{NCT_ID}_{medication}_v3.1_with_baseline.csv`

#### Outputs (22 files)

Generated in `project/{NCT_ID}/cohorts/{medication}/outputs/`:

**Main Analysis:**
- `matched_data_main.csv` - Matched cohort data
- `baseline_table_main_JAMA.md` - Table 1 (publication-ready)
- `main_analysis_cumulative_mortality.png` - Kaplan-Meier curve
- `main_survival_summary.csv` - HR, CI, p-values
- `balance_assessment_main.csv` - SMD report

**Sensitivity Analysis:**
- `matched_data_sensitivity.csv`
- `baseline_table_sensitivity_JAMA.md`
- `sensitivity_analysis_cumulative_mortality.png`
- `sensitivity_survival_summary.csv`
- `balance_assessment_sensitivity.csv`

**Reports:**
- `statistician_report.md` - LLM interpretation with all details
- `comparative_summary.md` - Main vs. sensitivity comparison

## API Endpoints

### List Available Agents

```http
GET /api/agents
```

**Response:**
```json
{
  "agents": [
    {
      "name": "statistician",
      "version": "0.1.0",
      "description": "Automated PSM + Survival Analysis..."
    }
  ]
}
```

### Run Agent

```http
POST /api/agents/{agent_name}/run
```

**Request Body:**
```json
{
  "agent_name": "statistician",
  "nct_id": "NCT03389555",
  "medication": "hydrocortisone na succ.",
  "config_overrides": {}
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "statistician",
  "status": "pending",
  "message": "Agent execution started"
}
```

### Poll Job Status

```http
GET /api/agents/jobs/{job_id}/status
```

**Response (in progress):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": "Executing PSM workflow...",
  "result": null,
  "error": null
}
```

**Response (completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": null,
  "result": {
    "success": true,
    "output": {
      "cohort_summary": {...},
      "psm_results": {...},
      "interpretation": "..."
    },
    "metadata": {
      "nct_id": "NCT03389555",
      "medication": "hydrocortisone na succ."
    }
  },
  "error": null
}
```

## Adding New Agents

### Step 1: Implement BaseAgent

Create `agents/{agent_name}/agent.py`:

```python
from agents.base import BaseAgent, AgentResult
from typing import Optional

class MyAgent(BaseAgent):
    def __init__(self):
        self.name = "my_agent"
        self.version = "0.1.0"
        self.description = "Description of what this agent does"

    async def validate_inputs(self, **kwargs) -> tuple[bool, Optional[str]]:
        # Validate required parameters
        if "required_param" not in kwargs:
            return False, "required_param is required"
        return True, None

    async def run(self, **kwargs) -> AgentResult:
        try:
            # Your agent logic here
            result = do_something(kwargs)

            return AgentResult(
                success=True,
                output=result,
                metadata={},
                error=None
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output={},
                metadata={},
                error=str(e)
            )

    def get_output_files(self, output_dir: str) -> list[Path]:
        # Return list of generated files
        return []
```

### Step 2: Register Agent

In `agents/{agent_name}/__init__.py`:

```python
from agents import register_agent
from agents.{agent_name}.agent import MyAgent

# Registration happens through decorator in agent.py
__all__ = ["MyAgent"]
```

### Step 3: Import in Main Registry

In `agents/__init__.py`:

```python
# Import agents to register them
try:
    from agents.my_agent import MyAgent
except ImportError:
    pass
```

### Step 4: Add Frontend Types

In `frontend/src/remote/types/agents.ts`:

```typescript
export interface MyAgentOutput {
  // Define agent-specific output structure
}
```

### Step 5: Test

```python
from agents import get_agent

agent = get_agent("my_agent")
result = await agent.run(required_param="value")
assert result.success
```

## Configuration

### Environment Variables

```bash
# Required for Statistician Agent
OPENROUTER_API_KEY=your-openrouter-key

# Optional workspace root
WORKSPACE_ROOT=./project
```

### Prompt Templates

Statistician Agent uses YAML prompts in `config/prompts/statistician_prompts.yaml`:

```yaml
config:
  model:
    default: "openai/gpt-4o-mini"
  temperature:
    parameter_recommendation: 0.7
    results_interpretation: 0.3

system_messages:
  parameter_recommendation: "You are an expert biostatistician..."
  results_interpretation: "You are an expert clinical biostatistician..."

prompts:
  parameter_recommendation:
    template: |
      Analyze the following baseline data and recommend optimal PSM parameters...
```

## Design Principles

### 1. Single Responsibility
- Each agent handles ONE analytical workflow
- Delegates to specialized modules (e.g., PSM, survival analysis)

### 2. Dependency Injection
- All external dependencies passed as parameters
- No hardcoded paths or API keys

### 3. Interface Segregation
- BaseAgent defines minimal interface
- Agents implement only what they need

### 4. Registry Pattern
- Centralized agent discovery
- No manual imports in application code

### 5. Clean Code
- Logging instead of print statements
- Type annotations throughout
- Comprehensive docstrings

## Testing

### Unit Tests

```bash
cd backend
pytest tests/agents/test_statistician_utils.py -v
```

**Coverage:**
- ✅ `sanitize_medication_name` (5 tests)
- ✅ `validate_nct_id` (5 tests)
- ✅ `validate_medication` (5 tests)
- ✅ `construct_cohort_path` (3 tests)
- ✅ `construct_output_dir` (3 tests)

### Integration Test

```bash
# With real NCT03389555 data
python -c "
import asyncio
from agents import get_agent

async def test():
    agent = get_agent('statistician')
    result = await agent.run(
        nct_id='NCT03389555',
        medication='hydrocortisone na succ.',
        openrouter_api_key='your-key'
    )
    print('Success:', result.success)

asyncio.run(test())
"
```

## Troubleshooting

### "Cohort file not found"

**Cause:** Agent can't find the baseline cohort file.

**Solution:** Ensure Phase 3 completed successfully:
```bash
ls project/NCT03389555/cohorts/hydrocortisonenasucc/
# Should see: NCT03389555_hydrocortisonenasucc_v3.1_with_baseline.csv
```

### "OPENROUTER_API_KEY not provided"

**Cause:** Missing OpenRouter API key.

**Solution:**
```bash
export OPENROUTER_API_KEY='your-key-here'
# Or pass as parameter: openrouter_api_key='...'
```

### "Module 'langchain' not found"

**Cause:** Missing dependencies.

**Solution:**
```bash
pip install langchain langchain-core langchain-openai langgraph pyyaml
```

## Performance

### Statistician Agent Benchmarks

**Hardware:** M1 Mac, 16GB RAM
**Data:** NCT03389555, 1,234 patients

| Stage | Duration | Notes |
|-------|----------|-------|
| Analyze Baseline | 2-3s | Pure pandas |
| Recommend Params | 5-8s | GPT-4o-mini API |
| Execute PSM | 30-45s | PSM + Cox + plots |
| Interpret Results | 8-12s | GPT-4o-mini API |
| **Total** | **45-68s** | End-to-end |

**Cost:** ~$0.01 per execution (2 LLM calls @ $0.005 each)

## Roadmap

### Planned Agents

- **TrialistAgent** - Automated trial criteria extraction from literature
- **CohortBuilderAgent** - Intelligent cohort selection and optimization
- **OutcomeAnalystAgent** - Advanced causal inference and HTE analysis
- **ReportWriterAgent** - Automated manuscript generation

### Features

- [ ] Agent chaining (pipeline multiple agents)
- [ ] Parallel agent execution
- [ ] Agent feedback loops (human-in-the-loop)
- [ ] Agent versioning and rollback
- [ ] Agent performance monitoring

## References

- **LangGraph**: https://github.com/langchain-ai/langgraph
- **OpenRouter**: https://openrouter.ai/
- **PSM**: Austin PC. An Introduction to Propensity Score Methods. JAMA. 2011.
- **Survival Analysis**: Kleinbaum DG, Klein M. Survival Analysis. Springer. 2012.
