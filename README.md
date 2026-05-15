# Machine Learning PJ

직업 기반 수강 추천 RAG 챗봇 프로젝트입니다. 사용자가 희망 직업 카테고리를 선택하면 2026-1학기 개설 과목 데이터, 수강편람 설명, 일부 과목 강의계획서를 바탕으로 관련 수업 Top 3~5개를 추천합니다.

## 프로젝트 목표

대학생은 수강편람에서 많은 과목을 직접 비교해야 하므로 진로와 연결되는 수업을 찾기 어렵습니다. 이 프로젝트는 직업별 키워드, 과목 설명 검색, 개설 과목 필터링, LLM 기반 추천 이유 생성을 결합해 진로 중심 수강 추천을 제공합니다.

## 현재 구현된 기능

- Streamlit 기반 웹 UI
- 희망 직업 카테고리 선택
- 2026-1학기 실제 개설 과목 CSV 반영
- SQLite DB 생성
- ChromaDB 벡터스토어 생성 구조
- OpenAI Embedding 기반 RAG 검색 구조
- GPT-4o-mini 기반 추천 이유 생성 구조
- API 없이 확인 가능한 데모 모드
- 추천 결과 카드 UI
- 추천 과목 CSV 내보내기
- 추천 과목 저장 기능
- 직업 A/B 추천 비교 기능
- 현재 추천된 수업 context 기반 추가 질문 기능
- 일부 과목 강의계획서 표시 기능
  - `MAT4088 머신러닝`
  - `MAT3030 일반위상수학`

## 지원 직업 카테고리

- AI 연구자
- 데이터 분석가
- 백엔드 / 소프트웨어 개발자
- 금융권 / 핀테크 / 퀀트
- UX 디자이너

## 시스템 구조

```text
사용자 입력
-> 직업별 키워드 조회
-> 과목 description 기반 검색
-> 2026-1학기 개설 과목 필터링
-> LLM 추천 이유 생성
-> Streamlit 추천 카드 출력
-> 선택 과목 강의계획서 확인
```

API 연결 전 데모 모드에서는 ChromaDB/OpenAI 대신 SQLite와 키워드 매칭으로 화면과 흐름을 먼저 확인합니다.

## 폴더 구조

```text
project/
├── app.py
├── rag_pipeline.py
├── db_utils.py
├── data_pipeline.py
├── config.py
├── requirements.txt
├── README.md
├── data/
│   ├── sample_courses.csv
│   ├── sample_semester_open.csv
│   ├── job_keywords.csv
│   ├── real_courses_2026_1.csv
│   ├── real_semester_open_2026_1.csv
│   └── course_syllabus.csv
├── db/
│   └── courses.db
├── vectorstore/
│   └── chroma/
├── logs/
│   ├── AI_USAGE_LOG.md
│   └── VALIDATION_LOG.md
└── evaluation/
    └── ragas_eval_template.py
```

## 주요 파일 설명

- `app.py`: Streamlit 프론트엔드입니다. 추천 화면, 비교 탭, 추가 질문, 저장 기능, 강의계획서 표시를 담당합니다.
- `rag_pipeline.py`: 추천 백엔드 로직입니다. 키워드 조회, 검색, 개설 과목 필터링, 추천 이유 생성, 강의계획서 조회를 담당합니다.
- `data_pipeline.py`: CSV에서 SQLite DB를 생성하고 ChromaDB 벡터스토어를 만드는 데이터 파이프라인입니다.
- `db_utils.py`: SQLite 연결과 공통 조회 유틸입니다.
- `config.py`: 경로, 모델명, 기본 학기, 지원 직업 카테고리를 관리합니다.
- `data/real_courses_2026_1.csv`: 실제 2026-1 개설 과목 기반 데이터입니다.
- `data/course_syllabus.csv`: 강의계획서 데이터입니다.

## 설치 방법

```bash
cd ~/Desktop/project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실행 방법: API 없이 데모 모드

OpenAI API 결제나 키 설정 전에는 데모 모드로 UI와 추천 흐름을 확인할 수 있습니다.

```bash
cd ~/Desktop/project
source .venv/bin/activate
python data_pipeline.py --db --real-data
streamlit run app.py
```

Streamlit 화면이 열리면 사이드바에서 `API 없이 데모 모드`를 켜고 `수업 추천받기`를 누릅니다.

## 실행 방법: OpenAI API 연결

OpenAI API를 연결하면 키워드 매칭이 아니라 Embedding 기반 의미 검색과 GPT 추천 이유 생성을 사용할 수 있습니다.

```bash
cd ~/Desktop/project
source .venv/bin/activate
export OPENAI_API_KEY="sk-..."
python data_pipeline.py --db --real-data
python rag_pipeline.py --build-vectorstore
streamlit run app.py
```

API 모드에서는 사이드바의 `API 없이 데모 모드`를 끄고 추천을 실행합니다.

## DB 생성

샘플 데이터로 DB를 만들려면:

```bash
python data_pipeline.py
```

실제 2026-1 수강편람 기반 CSV로 DB를 만들려면:

```bash
python data_pipeline.py --db --real-data
```

DB를 다시 만들면 기존 `db/courses.db`는 초기화됩니다.

## ChromaDB 생성

OpenAI API Key 설정 후 실행합니다.

```bash
python rag_pipeline.py --build-vectorstore
```

실제 과목 CSV를 수정했다면 DB를 다시 만든 뒤 ChromaDB도 다시 생성해야 검색 결과가 최신 데이터와 일치합니다.

## 강의계획서 기능

현재 `data/course_syllabus.csv`에는 다음 과목의 강의계획서가 들어 있습니다.

- `MAT4088 머신러닝`
- `MAT3030 일반위상수학`

추천 결과에 해당 과목이 나오면 카드 아래의 `강의계획서 보기`를 펼쳐 교과목개요, 수업목표, 선수과목 안내, 교재, 평가항목, 주별 강의계획을 확인할 수 있습니다.

## 예시 사용 흐름

1. `streamlit run app.py` 실행
2. 사이드바에서 `API 없이 데모 모드` 켜기
3. 직업 카테고리에서 `데이터 분석가` 선택
4. `수업 추천받기` 클릭
5. 추천 결과에서 `머신러닝` 카드 확인
6. `강의계획서 보기` 펼치기
7. 추가 질문 탭에서 `머신러닝은 선수과목이 필요해?` 질문

## 예시 질문

- 데이터 분석가에게 가장 중요한 수업은 뭐야?
- 머신러닝은 선수과목이 필요해?
- AI 연구자에게 딥러닝 수업이 왜 좋아?
- 백엔드 개발자에게 운영체제론이 도움이 돼?
- UX 디자이너에게 HCI 수업이 왜 관련 있어?

## 데이터 업데이트 방법

과목을 추가하거나 수정하려면 아래 파일을 수정합니다.

- 과목 정보: `data/real_courses_2026_1.csv`
- 개설 여부: `data/real_semester_open_2026_1.csv`
- 직업별 키워드: `data/job_keywords.csv`
- 강의계획서: `data/course_syllabus.csv`

수정 후 DB를 다시 생성합니다.

```bash
python data_pipeline.py --db --real-data
```

API 모드까지 사용할 경우 벡터스토어도 다시 생성합니다.

```bash
python rag_pipeline.py --build-vectorstore
```

## 팀원 역할 분담 예시

- 데이터 담당: 수강편람 CSV 정리, 강의계획서 CSV 추가, 중복 과목 정리
- RAG 담당: ChromaDB 검색 품질 개선, 프롬프트 개선, 추천 로직 조정
- 백엔드 담당: SQLite 스키마, 데이터 파이프라인, 예외 처리
- 프론트엔드 담당: Streamlit UI, 추천 카드, 강의계획서 화면, 비교 기능
- 평가 담당: RAGAS 평가 데이터셋 구성, Faithfulness/Answer Relevancy/Context Recall 평가

## GitHub 협업 방법

처음 clone한 팀원은 아래 순서로 실행합니다.

```bash
git clone <repository-url>
cd machine_learning_pj
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python data_pipeline.py --db --real-data
streamlit run app.py
```

각자 작업할 때는 기능별 브랜치를 만들어 작업하는 것을 권장합니다.

```bash
git checkout -b feature/syllabus-ui
```

## 향후 확장 계획

- 더 많은 핵심 과목 강의계획서 추가
- 슥삭 등 외부 대외활동 링크 추천 fallback
- 실제 수강편람 description 보강
- 사용자 전공/학년/이수 과목 기반 개인화 추천
- RAGAS 기반 정량 평가 연결
- 추천 결과에 사용자 피드백 저장 및 재랭킹
