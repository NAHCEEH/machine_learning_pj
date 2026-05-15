# Validation Log

| 검증 항목 | 검증 방법 | 발견된 문제 | 수정 내용 | 재검증 결과 |
|---|---|---|---|---|
| 예: SQLite DB 생성 | `python data_pipeline.py --db` 실행 | 예: 컬럼 타입 불일치 | 예: CSV 변환 로직 수정 | 예: 정상 생성 확인 |
| 예: ChromaDB 임베딩 생성 | `python data_pipeline.py --vectorstore` 실행 | 예: OPENAI_API_KEY 누락 | 예: 명확한 에러 메시지 추가 | 예: 키 설정 후 정상 생성 |
| 예: Streamlit 추천 UI | `streamlit run app.py` 실행 | 예: 추천 결과 없음 | 예: 샘플 데이터 키워드 보강 | 예: 직업별 3~5개 출력 확인 |
