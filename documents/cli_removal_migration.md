# CLI 제거 및 Pipeline 모듈 마이그레이션

## 📅 마이그레이션 일자
2025-10-13

## 🎯 목적
- CLI 인터페이스를 완전히 제거하고 FastAPI 백엔드만 사용
- Core 로직을 `src/pipeline/` 모듈로 재구성
- API 중심의 아키텍처로 전환

## 📦 변경 사항

### 1. 디렉토리 구조 변경

#### Before
```
src/
├── rwe_cli/              # CLI 인터페이스 + Core 로직
│   ├── __main__.py      # CLI entry point (제거됨)
│   ├── cli.py           # CLI commands (제거됨)
│   ├── config.py        # Config loader (제거됨)
│   ├── models.py        # → pipeline/models.py
│   ├── context.py       # → pipeline/context.py
│   ├── serialization.py # → pipeline/serialization.py
│   └── plugins/         # → pipeline/plugins/
└── rwe_api/             # FastAPI app
```

#### After
```
src/
├── pipeline/             # ✨ Pipeline core logic (NEW)
│   ├── __init__.py
│   ├── models.py        # Data models
│   ├── context.py       # Pipeline context
│   ├── utils.py         # Utility functions (NEW)
│   ├── serialization.py # Data serialization
│   └── plugins/         # Pipeline implementations
│       ├── __init__.py
│       ├── defaults.py  # Synthetic implementations
│       ├── langgraph_search.py
│       ├── langgraph_parser.py
│       └── mimic_demo.py
└── rwe_api/             # FastAPI application
    ├── main.py
    ├── routes/
    ├── schemas/
    └── services/
```

### 2. 새로 생성된 파일

#### `src/pipeline/__init__.py`
Pipeline 모듈의 공개 API 정의:
```python
from . import models
from .context import PipelineContext
from .plugins import registry
from .serialization import write_json, write_jsonl
```

#### `src/pipeline/utils.py`
CLI에서 추출한 유틸리티 함수들:
- `resolve_impl_name()` - 구현체 이름 해석
- `stage_path()` - 워크스페이스 경로 생성
- `load_corpus_from_disk()` - 문헌 데이터 로드
- `load_schema_from_disk()` - 스키마 로드
- `load_filter_spec_from_disk()` - 필터 스펙 로드
- `load_cohort_from_disk()` - 코호트 결과 로드
- `load_analysis_from_disk()` - 분석 결과 로드
- `parse_variations()` - Stimula 변수 파싱
- `load_config()` - 설정 파일 로드
- `load_variable_dictionary()` - 변수 사전 로드

### 3. Import 경로 변경

#### `src/rwe_api/services/pipeline_service.py`
```python
# Before
from rwe_cli import models
from rwe_cli.cli import load_corpus_from_disk, ...
from rwe_cli.config import load_config
from rwe_cli.context import create_context
from rwe_cli.plugins import registry
from rwe_cli.serialization import ...

# After
from pipeline import models
from pipeline.utils import (
    load_corpus_from_disk,
    load_schema_from_disk,
    load_config,
    stage_path,
    ...
)
from pipeline.context import create_context
from pipeline.plugins import registry
from pipeline.serialization import ...
```

### 4. 제거된 파일
- `src/rwe_cli/__main__.py` - CLI entry point
- `src/rwe_cli/cli.py` - CLI command definitions
- `src/rwe_cli/config.py` - Configuration loader
- 전체 `src/rwe_cli/` 디렉토리

## ✅ 마이그레이션 검증

### 1. 서버 시작
```bash
cd /Users/kyh/datathon
source venv/bin/activate
PYTHONPATH=src uvicorn rwe_api.main:app --reload --port 8000
```

### 2. Health Check
```bash
curl http://localhost:8000/health
# ✅ {"status": "healthy", "workspace_root": "workspace", "workspace_exists": true}
```

### 3. Search API Test
```bash
curl -X POST "http://localhost:8000/api/pipeline/search-lit" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test",
    "disease_code": "",
    "keywords": ["NCT04134403"],
    "sources": ["clinicaltrials"],
    "impl": "langgraph-search"
  }'
# ✅ Status: success
# ✅ Documents: 1
# ✅ Full data preserved
```

## 📊 영향 분석

### 긍정적 효과
1. **단순화된 아키텍처**: CLI 레이어 제거로 코드 복잡도 감소
2. **명확한 책임 분리**: 
   - `pipeline/` - Core 로직과 데이터 모델
   - `rwe_api/` - API 인터페이스
3. **개선된 유지보수성**: 단일 진입점(FastAPI)으로 통합
4. **타입 안정성**: Pydantic 스키마로 API 계약 명확화

### 주의 사항
1. **CLI 의존성 제거**: 
   - 이전 CLI 명령어는 더 이상 사용 불가
   - 모든 작업은 API를 통해 수행
2. **Import 경로 변경**:
   - `rwe_cli` → `pipeline`
   - 기존 스크립트가 있다면 업데이트 필요

## 🔄 마이그레이션 체크리스트

- [x] Core 로직을 `src/pipeline/`으로 이동
- [x] 유틸리티 함수를 `pipeline/utils.py`에 추출
- [x] `rwe_api` import 경로 업데이트
- [x] CLI 디렉토리 제거
- [x] 서버 정상 동작 확인
- [x] API 엔드포인트 테스트
- [x] README.md 업데이트
- [x] 문서화 완료

## 📝 추가 작업 필요

### 문서 업데이트
- [x] `README.md` - 프로젝트 구조 업데이트
- [x] `documents/langgraph_parser_usage.md` - CLI 예시 제거, API 예시 추가
- [ ] `documents/cli_modules.md` - "Pipeline Modules"로 이름 변경 고려

### 테스트
- [ ] 모든 pipeline 단계 통합 테스트
- [ ] Playwright MCP를 통한 E2E 테스트

## 🚀 향후 계획

1. **Frontend 연동 강화**: 모든 pipeline 단계를 UI에서 실행 가능하도록
2. **실시간 상태 업데이트**: WebSocket을 통한 파이프라인 진행 상황 스트리밍
3. **배치 처리**: 여러 프로젝트 동시 처리 기능
4. **캐싱 전략**: Redis를 통한 중간 결과 캐싱

## 📚 관련 문서

- [API Specification](./api_specification.md)
- [LangGraph Search Usage](./langgraph_search_usage.md)
- [LangGraph Parser Usage](./langgraph_parser_usage.md)
- [MIMIC Demo Data Usage](./mimic_demo_data_usage_ko.md)

