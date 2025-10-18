from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
import pandas as pd
import numpy as np
import shap
from datetime import datetime
import os
from openai import OpenAI
import json
import xgboost as xgb
import numpy as np
import joblib


# State 정의
class ExtubationPredictionState(TypedDict):
    """전체 워크플로우에서 사용되는 상태"""
    # 입력 데이터
    patient_input: Optional[dict]  # 사용자 입력 데이터
    patient_data: Optional[pd.DataFrame]
    tagging_model: Optional[str]
    generation_model: Optional[str]

    # Ontology 태깅 결과
    ontology_features: Optional[dict]
    feature_matrix: Optional[np.ndarray]
    feature_names: Optional[list]

    # ML 모델 및 예측 결과
    model: Optional[xgb.Booster]
    prediction_result: Optional[dict]

    # SHAP 분석 결과
    shap_values: Optional[np.ndarray]
    shap_explanation: Optional[dict]

    # 최종 레포트
    report: Optional[str]

    # 에러 핸들링
    error: Optional[str]


# Node 1: 사용자 입력 데이터 처리
def process_user_input(state: ExtubationPredictionState) -> ExtubationPredictionState:
    """
    사용자로부터 입력받은 환자 데이터 처리
    """
    try:
        patient_input = state["patient_input"]

        # 필수 feature 체크
        required_features = ['AGE', 'SEX', 'BMI', 'VENT_DUR', 'CHF', 'CVD', 'CPD', 'CKD', 'CLD', 'DM', 'CRRT', 'CVP', 'MAP', 'HR', 'RR', 'BT', 'SPO2', 'GCS', 'PH', 'PACO2', 'PAO2', 'HCO3', 'LACTATE', 'WBC', 'HB', 'PLT', 'SODIUM', 'POTASSIUM', 'CHLORIDE', 'BUN', 'CR', 'TB', 'PT', 'FIO2', 'PEEP', 'PPLAT', 'TV', 'obesity_importance',
       'advanced_age_importance', 'male_sex_importance',
       'high_fraction_of_inspired_oxygen_importance',
       'diabetes_mellitus_history_importance', 'acidosis_importance',
       'anemia_importance', 'elevated_blood_urea_nitrogen_importance',
       'tachycardia_importance', 'low_mean_arterial_pressure_importance']
        
        missing_features = [f for f in required_features if f not in patient_input]
        
        if missing_features:
            return {
                **state,
                "error": f"Missing required features: {missing_features}"
            }

        # DataFrame으로 변환 (1개 행)
        df = pd.DataFrame([patient_input])
        sex_map = {"M": 0, "F": 1, "F": 0, "M": 1, 0: 0, 1: 1}
        df["SEX"] = df["SEX"].map(sex_map).astype(float)

        # 필수 컬럼만 선택 (순서 유지)
        df = df[required_features]
        required_cols = ["SODIUM", "CHLORIDE", "HCO3"]
        if all(col in df.columns for col in required_cols):
            df["ANION_GAP"] = df["SODIUM"] - df["CHLORIDE"] - df["HCO3"]

        print(f"  Features: {list(df.columns)}")

        return {
            **state,
            "patient_data": df,
            "error": None
        }

    except Exception as e:
        return {
            **state,
            "error": f"Input processing error: {str(e)}"
        }


# Node 2: Ontology Feature 태깅 (LLM 사용)
def tag_ontology_features(state: ExtubationPredictionState) -> ExtubationPredictionState:
    """
    LLM을 사용한 의료 온톨로지 기반 특성 태깅
    """
    try:
        df = state["patient_data"]

        # OpenAI 클라이언트 초기화
        client = OpenAI(base_url="your_endpoint_url", api_key="your_api_key")

        # 환자 데이터를 JSON 형태로 변환
        patient_records = df.to_dict(orient='records')
        # assert False

        # LLM 프롬프트 구성
        prompt = f"""
너는 중환자실 전문의이자 임상 데이터 전문가야.
아래 변수들이 환자의 '발관 실패(Extubation Failure)' 예측에 얼마나 중요한지를 판단해줘.

환자 데이터:
{json.dumps(patient_records, indent=2, ensure_ascii=False)}

질문:
1. obesity_importance
2. advanced_age_importance
3. male_sex_importance
4. high_fraction_of_inspired_oxygen_importance
5. diabetes_mellitus_history_importance
6. acidosis_importance
7. anemia_importance
8. elevated_blood_urea_nitrogen_importance
9. tachycardia_importance
10. low_mean_arterial_pressure_importance
위 변수들은 기관 발관 실패를 예측하는 데 중요한 변수인가? (주어진 환자 데이터를 사용하여 답변하세요)

응답 규칙:
- 매우 중요하거나 중요한 경우: 1
- 중요하지 않거나 관련이 없는 경우: 0:


응답은 반드시 다음 JSON 형식으로만 제공해주세요:
{{
  "patients": [
    {{
      "obesity_importance": 0 or 1,
      "advanced_age_importance": 0 or 1,
      "male_sex_importance": 0 or 1,
      "high_fraction_of_inspired_oxygen_importance": 0 or 1,
      "diabetes_mellitus_history_importance": 0 or 1,
      "acidosis_importance": 0 or 1,
      "anemia_importance": 0 or 1,
      "elevated_blood_urea_nitrogen_importance": 0 or 1,
      "tachycardia_importance": 0 or 1,
      "low_mean_arterial_pressure_importance": 0 or 1,
    }}
  ]
}}

주의: JSON 형식 외의 다른 설명은 포함하지 마세요.
"""

        print("\n\n🤖 Calling LLM for ontology tagging...")

        # LLM 호출
        response = client.chat.completions.create(
            model=state["tagging_model"],
            messages=[
                {"role": "system", "content": "너는 중환자실 전문의이자 임상 데이터 전문가야. 주어진 변수의 중요도를 1 또는 0으로만 평가해줘."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # LLM 응답 파싱
        llm_output = json.loads(response.choices[0].message.content)

        # 온톨로지 특성 추출
        ontology_features = {}
        feature_names = ['obesity_importance',
       'advanced_age_importance', 'male_sex_importance',
       'high_fraction_of_inspired_oxygen_importance',
       'diabetes_mellitus_history_importance', 'acidosis_importance',
       'anemia_importance', 'elevated_blood_urea_nitrogen_importance',
       'tachycardia_importance', 'low_mean_arterial_pressure_importance']

        for feature_name in feature_names:
            feature_values = [
                patient.get(feature_name, 0)
                for patient in llm_output["patients"]
            ]
            ontology_features[feature_name] = pd.Series(feature_values, dtype=int)
            print(f"Ontology feature: {feature_name}, Value: {feature_values}")

        # Feature matrix 생성 (원본 데이터 + 온톨로지 특성)
        feature_df = df.copy()
        for feature_name, feature_values in ontology_features.items():
            feature_df[feature_name] = feature_values

        feature_matrix = feature_df.values

        # Feature 이름 리스트 저장 (순서 유지)
        feature_names_list = feature_df.columns.tolist()

        print(f"✓ LLM tagged {len(ontology_features)} ontology features")
        print(f"  Features: {', '.join(ontology_features.keys())}")

        return {
            **state,
            "ontology_features": ontology_features,
            "feature_matrix": feature_matrix,
            "feature_names": feature_names_list,
            "error": None
        }

    except Exception as e:
        return {
            **state,
            "error": f"Ontology tagging error: {str(e)}"
        }


# Node 3: ML 예측 (사전 학습된 XGBoost 모델 사용)
def predict_extubation_failure(state: ExtubationPredictionState) -> ExtubationPredictionState:
    """
    사전 학습된 XGBoost 모델을 사용하여 발관 실패 확률 예측
    """
    try:
        feature_matrix = state["feature_matrix"]
        model_path = "./models/best_model_medgemma.pkl"
        
        # 모델 존재 여부 확인
        if not os.path.exists(model_path):
            return {
                **state,
                "error": f"Model not found at {model_path}. Please train the model first."
            }

        # 사전 학습된 모델 로드
        model = joblib.load(model_path)
        print(f"\n\n✓ Loaded pre-trained model from {model_path}")


        feature_matrix = np.array(feature_matrix)
        
        # 모델에서 학습 시 사용된 컬럼 이름 가져오기
        feature_names = model.input_feature_names

        # feature_matrix를 DataFrame으로 변환
        feature_matrix = pd.DataFrame(feature_matrix, columns=feature_names if feature_matrix.shape[1] == len(feature_names) else None)
        
        predictions = model.predict_proba(feature_matrix)[:, 1]

        # 확률 값 추출 (이진 분류의 경우)
        failure_probability = float(predictions[0])
        predicted_class = 1 if failure_probability > 0.3 else 0

        print(f"✓ XGBoost Prediction: {failure_probability:.2%} failure probability")
        print(f"  Predicted class: {'실패 예상' if predicted_class == 1 else '성공 예상'}")

        prediction_result = {
            "probability": failure_probability,
            "class": int(predicted_class)
        }

        return {
            **state,
            "model": model,
            "prediction_result": prediction_result,
            "error": None
        }

    except Exception as e:
        return {
            **state,
            "error": f"Prediction error: {str(e)}"
        }


# Node 4: SHAP Value 계산
def calculate_shap_values(state: ExtubationPredictionState) -> ExtubationPredictionState:
    """
    SHAP (SHapley Additive exPlanations) 값 계산
    각 feature가 예측에 미치는 영향도 분석
    """
    try:
        model = state["model"]
        feature_matrix = state["feature_matrix"]
        feature_names = model.input_feature_names
    
        if model is None:
            return {
                **state,
                "error": "Model not found in state. Cannot calculate SHAP values."
            }
    
        print("\n\n🔍 Calculating SHAP values...")
    
        # DMatrix로 변환
        feature_matrix = np.array(feature_matrix)
    
        feature_names = model.input_feature_names
    
        # feature_matrix를 DataFrame으로 변환
        feature_matrix = pd.DataFrame(feature_matrix, columns=feature_names if feature_matrix.shape[1] == len(feature_names) else None)
        
        preprocessor = model.named_steps.get("preprocess", None)  # 이름이 다를 수 있음
        final_estimator = model.named_steps["model"]      # 마지막 모델 단계
        feature_matrix_transformed = preprocessor.transform(feature_matrix)
    
        
        # SHAP explainer 생성 및 값 계산
        explainer = shap.TreeExplainer(final_estimator)
        shap_values = explainer.shap_values(feature_matrix_transformed)
        shap_values_sample = np.array(shap_values)[0,:,1]
        
        # Feature 중요도 정리
        shap_explanation = {
            "feature_importance": {
                name: float(shap_values_sample[i])
                for i, name in enumerate(feature_names)
            },
            "top_risk_factors": sorted(
                [(name, abs(float(shap_values_sample[i])))
                 for i, name in enumerate(feature_names)],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
        print(f"✓ Calculated SHAP values for {len(feature_names)} features")
        print(f"  Top risk factor: {shap_explanation['top_risk_factors'][0][0]}")
        print(f"  Top 5 Risk factors: {shap_explanation['top_risk_factors']}")
    
        return {
            **state,
            "shap_values": shap_values,
            "shap_explanation": shap_explanation,
            "error": None
        }

    except Exception as e:
        return {
            **state,
            "error": f"SHAP calculation error: {str(e)}"
        }


# Node 5: 보호자 설명용 레포트 생성
def generate_report(state: ExtubationPredictionState) -> ExtubationPredictionState:
    """
    LLM을 사용하여 ML 예측 결과와 SHAP 값을 활용한 보호자용 설명 레포트 생성
    """
    try:
        prediction = state["prediction_result"]
        shap_exp = state["shap_explanation"]
        patient_input = state["patient_input"]

        # OpenAI 클라이언트 초기화
        client = OpenAI(base_url="your_endpoint_url", api_key="your_api_key")

        # 확률 값
        probability = prediction['probability']
        predicted_class = prediction['class']

        # 주요 위험 요인을 딕셔너리 형태로 준비
        top_risk_factors = []
        for factor, importance in shap_exp["top_risk_factors"]:
            # impact_direction = "위험도 증가" if shap_exp["feature_importance"][factor] > 0 else "위험도 감소"
            top_risk_factors.append({
                "feature_name": factor,
                "importance_score": round(importance, 4),
                # "impact": impact_direction
            })

        # LLM 프롬프트 구성
        prompt = f"""
당신은 의료진과 환자 보호자 사이의 소통을 돕는 의료 커뮤니케이션 전문가입니다.
아래 인공지능 예측 결과를 바탕으로 보호자가 이해하기 쉬운 설명 레포트를 작성해주세요.

## 입력 데이터

### 환자 정보
{json.dumps(patient_input, indent=2, ensure_ascii=False)}

### AI 예측 결과
- 발관(인공호흡기 튜브 제거) 실패 확률: {probability:.1%}
- 예측 클래스: {predicted_class} (0=안전, 1=위험)

### 주요 위험 요인 (중요도 순위)
{json.dumps(top_risk_factors, indent=2, ensure_ascii=False)}

## 레포트 작성 지침

**목적**: 보호자가 발관(인공호흡기 튜브 제거) 결정을 내리는 데 도움이 되는 정보를 제공합니다.

**톤 & 스타일**:
- 따뜻하고 공감적인 어조를 유지하세요
- 보호자의 불안감을 이해하면서도 정확한 정보를 전달하세요
- 의학적 전문성과 인간미를 균형있게 표현하세요

**용어 선택**:
- 전문 의료 용어는 일반인이 이해하기 쉬운 표현으로 바꿔주세요
  예: "발관/삽관" → "호흡관 제거", "인공호흡기 튜브 제거"
  예: "SPO2" → "혈중 산소포화도" 또는 "산소 수치"
  예: "BMI" → "체질량지수" 또는 "비만도"
- Feature 이름(영어 또는 전문용어)은 한글로 의역하여 설명하세요

**설명 방식**:
- 확률 수치를 구체적인 예시나 비유로 쉽게 설명하세요
- 위험 요인이 왜 중요한지 보호자 입장에서 설명하세요
- 의료진의 모니터링과 전문적 판단이 중요함을 강조하세요

## 레포트 구성 (다음 순서로 작성)

1. **인사 및 소개** (2-3문장)
   - 따뜻한 인사와 레포트의 목적 설명

2. **환자 상태 요약** (3-4문장)
   - 제공된 환자 정보를 일반인이 이해할 수 있는 방식으로 요약
   - 각 수치가 정상 범위인지, 주의가 필요한지 간단히 설명

3. **AI 예측 결과 해석** (4-5문장)
   - 실패 확률이 의미하는 바를 쉽게 설명
   - 이 확률이 높은지 낮은지 맥락 제공
   - 예측이 절대적이 아닌 참고자료임을 명시

4. **주요 위험 요인 상세 설명** (각 요인당 2-3문장)
   - 상위 3-5개 위험 요인을 선택하여 설명
   - 각 요인이 왜 발관 성공/실패에 영향을 미치는지 설명
   - Feature 이름을 보호자가 이해할 수 있는 용어로 변환

5. **마무리 메시지** (2문장)
   - 안심과 격려의 메시지
   - 의료진의 전문성에 대한 신뢰 강조

**중요**: 레포트는 순수한 한글 텍스트로만 작성하고, 마크다운 서식(#, **, - 등)은 사용하지 마세요.
섹션 제목은 [섹션명] 형태로 표시하세요.
"""

        print("\n\n🤖 Calling LLM to generate patient-friendly report...")

        # LLM 호출
        response = client.chat.completions.create(
            model=state["generation_model"],
            messages=[
                {
                    "role": "system",
                    "content": "당신은 의료 정보를 일반인이 이해하기 쉽게 전달하는 의료 커뮤니케이션 전문가입니다. "
                               "복잡한 의학 정보를 따뜻하고 공감적인 방식으로 설명하며, 보호자가 올바른 의료 결정을 내릴 수 있도록 돕습니다."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )

        # LLM이 생성한 레포트
        llm_report = response.choices[0].message.content

        # 레포트 헤더와 푸터 추가
        report = f"""
{'='*60}
기계환기 발관 안내문
{'='*60}

생성 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}

{llm_report}

{'='*60}
본 안내문은 AI 기반 예측 시스템을 활용하여 작성되었습니다.
최종 의료 결정은 담당 의료진의 종합적인 판단에 따라 이루어집니다.
궁금한 점이나 우려사항이 있으시면 언제든 의료진에게 문의해 주세요.
{'='*60}
"""

        print("✓ Generated patient-friendly report using LLM")
        return {
            **state,
            "report": report,
            "error": None
        }

    except Exception as e:
        return {
            **state,
            "error": f"Report generation error: {str(e)}"
        }



# 에러 핸들러
def handle_error(state: ExtubationPredictionState) -> ExtubationPredictionState:
    """에러 발생 시 처리"""
    print(f"✗ Error occurred: {state['error']}")
    return state


# 조건부 엣지: 에러 체크
def check_error(state: ExtubationPredictionState) -> str:
    """에러가 있으면 에러 핸들러로, 없으면 다음 노드로"""
    if state.get("error"):
        return "error"
    return "continue"


# LangGraph 구성
def create_demo_graph():
    """발관 실패 예측 데모 그래프 생성"""

    workflow = StateGraph(ExtubationPredictionState)

    # 노드 추가
    workflow.add_node("process_input", process_user_input)
    workflow.add_node("tag_ontology", tag_ontology_features)
    workflow.add_node("predict", predict_extubation_failure)
    workflow.add_node("calculate_shap", calculate_shap_values)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("handle_error", handle_error)

    # 엣지 추가 (순차적 플로우)
    workflow.set_entry_point("process_input")

    # 조건부 엣지: 각 단계마다 에러 체크
    workflow.add_conditional_edges(
        "process_input",
        check_error,
        {
            "continue": "tag_ontology",
            "error": "handle_error"
        }
    )

    workflow.add_conditional_edges(
        "tag_ontology",
        check_error,
        {
            "continue": "predict",
            "error": "handle_error"
        }
    )

    workflow.add_conditional_edges(
        "predict",
        check_error,
        {
            "continue": "calculate_shap",
            "error": "handle_error"
        }
    )

    workflow.add_conditional_edges(
        "calculate_shap",
        check_error,
        {
            "continue": "generate_report",
            "error": "handle_error"
        }
    )

    workflow.add_edge("generate_report", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()


# 실행 함수
def run_demo_prediction(patient_input: dict, tagging_model: str, generation_model: str):
    """
    발관 실패 예측 데모 실행 (사용자 입력 기반)

    Args:
        patient_input: 환자 데이터 딕셔너리
            예시: {
                "AGE": 72,
                "BMI": 28.5,
                "SPO2": 88,
                "HEART_RATE": 105,
                "SYSTOLIC_BP": 145
            }

    Returns:
        최종 상태 (예측 결과, SHAP 값, 레포트 포함)
    """
    graph = create_demo_graph()

    initial_state = {
        "patient_input": patient_input,
        "tagging_model": tagging_model,
        "generation_model": generation_model,
        "patient_data": None,
        "ontology_features": None,
        "feature_matrix": None,
        "feature_names": None,
        "model": None,
        "prediction_result": None,
        "shap_values": None,
        "shap_explanation": None,
        "report": None,
        "error": None
    }

    print("\n" + "="*60)
    print("발관 실패 예측 데모 시작")
    print("="*60 + "\n")

    final_state = graph.invoke(initial_state)

    if final_state.get("report"):
        print(final_state["report"])

    return final_state


# 사용자 입력 받기
def get_user_input():
    """
    터미널에서 사용자 입력을 받아 환자 데이터 딕셔너리 생성
    """
    print("\n" + "="*60)
    print("환자 정보를 입력해주세요")
    print("="*60)

    # 예시입니다
    try:
        age = float(input("나이 (AGE): "))
        bmi = float(input("BMI: "))
        spo2 = float(input("산소포화도 (SPO2, %): "))
        heart_rate = float(input("심박수 (HEART_RATE, 회/분): "))
        systolic_bp = float(input("수축기 혈압 (SYSTOLIC_BP, mmHg): "))

        patient_input = {
            "AGE": age,
            "BMI": bmi,
            "SPO2": spo2,
            "HEART_RATE": heart_rate,
            "SYSTOLIC_BP": systolic_bp
        }

        return patient_input

    except ValueError as e:
        print(f"✗ 입력 오류: 숫자를 입력해주세요. ({e})")
        return None


# 사용 예시
if __name__ == "__main__":
    print("발관 실패 예측 데모 시스템")
    # 옵션 1: 사용자 입력으로 실행
    # patient_input = get_user_input()

    # 옵션 2: 하드코딩된 예시 데이터로 실행 (테스트용)
    patient_input = {'AGE': 82,
 'SEX': 'F',
 'BMI': 32.55668934,
 'VENT_DUR': 149.8666667,
 'CHF': 0,
 'CVD': 0,
 'CPD': 1,
 'CKD': 0,
 'CLD': 1,
 'DM': 1,
 'CRRT': 0,
 'CVP': 6.3,
 'MAP': 61.1,
 'HR': 93.0,
 'RR': 17.0,
 'BT': 93.4,
 'SPO2': 92.0,
 'GCS': 11.0,
 'PH': 7.5,
 'PACO2': 47.0,
 'PAO2': 115.1,
 'HCO3': 28.2,
 'LACTATE': 0.89,
 'WBC': np.nan,
 'HB': np.nan,
 'PLT': np.nan,
 'SODIUM': 136.1,
 'POTASSIUM': 3.1,
 'CHLORIDE': 102.0,
 'BUN': 23.0,
 'CR': 1.4,
 'TB': np.nan,
 'PT': np.nan,
 'FIO2': 40.2,
 'PEEP': 5.1,
 'PPLAT': np.nan,
 'TV': 620.0,
 'obesity_importance': 1,
 'advanced_age_importance': 1,
 'male_sex_importance': 1,
 'high_fraction_of_inspired_oxygen_importance': 1,
 'diabetes_mellitus_history_importance': 1,
 'acidosis_importance': 0,
 'anemia_importance': 0,
 'elevated_blood_urea_nitrogen_importance': 1,
 'tachycardia_importance': 1,
 'low_mean_arterial_pressure_importance': 1}

    ALLOWED_MODELS = ["gpt-oss-20b", "hari-q3", "medgemma-27b-text-it"]
    tagging_model = "medgemma-27b-text-it"
    generation_model = "medgemma-27b-text-it"
    
    assert tagging_model in ALLOWED_MODELS, f"Unknown tagging model name: {tagging_model}"
    assert generation_model in ALLOWED_MODELS, f"Unknown generation model name: {generation_model}"
    
    if patient_input:
        result = run_demo_prediction(patient_input, tagging_model, generation_model)

        # 결과 접근
        if result.get("prediction_result"):
            print(f"\n최종 예측: {result['prediction_result']}")

        if result.get("error"):
            print(f"\n에러 발생: {result['error']}")
