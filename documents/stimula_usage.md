# Stimula Agent(표시용 What-if) 사용 가이드

## 개요
- Stimula는 파이프라인 마지막에 위치하는 “표시용(계산 없이)” what-if 도구입니다.
- 현재 코호트(`cohort.json`)의 행을 기준으로 간단한 임계값 가정을 바꿔가며, 포함 유지/탈락 인원과 비율을 빠르게 확인합니다.
- 기본 3가지 값(variation)까지 스위프하며, 값 개수는 `--max-variations`로 조절할 수 있습니다.

지원 키(초기 버전)
- `LVEF_LT`: LVEF < 임계값
- `AGE_MIN`: age > 임계값
- `AGE_MAX`: age < 임계값
- `BNP_GT`: BNP > 임계값

주의: 표시용이므로 EHR 재쿼리나 분석 재계산은 하지 않습니다. 프론트엔드 통합 시 신속한 상호작용을 위한 사전 요약 자료로 쓰입니다.

## 실행 예시
```bash
# 기본 3-variation 스위프 (표시용)
PYTHONPATH=src python -m rwe_cli \
  --project demo --workspace workspace \
  stimula \
  --vary LVEF_LT=35,40,45 \
  --vary AGE_MIN=50,60
```

산출물
- `workspace/<project>/stimula/sweep_results.jsonl`: 시나리오별 결과
- `workspace/<project>/stimula/manifest.json`: 요약 메타데이터
- `workspace/<project>/stimula/plan.json`: 실행 계획(키, 최대 variation 수)

## 출력 예(요약)
- variation: `LVEF_LT=35`
- kept_subjects: 106 / dropped_subjects: 41 / keep_rate: 0.72
- sample_subjects: ["10009628", "10018081", ...]

## 한계와 다음 단계
- 단일 임계값 기준만 지원(복합 조건 그리드는 추후 확장)
- 계산 없이 표시만 하므로, 해석은 참고용으로 제한
- 추후 프론트(대시보드)에서 실시간 조작 → 증분 필터·분석과 연동 예정
