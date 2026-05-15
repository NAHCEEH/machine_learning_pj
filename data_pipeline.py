"""Create sample CSV files, build SQLite DB, and create ChromaDB embeddings.

Typical usage:
    python data_pipeline.py --all

If OPENAI_API_KEY is not set, CSV and DB creation still work, but vectorstore
creation stops with a clear error message.
"""

import argparse
import csv
import os
import shutil
import sqlite3
import sys
from pathlib import Path

from config import (
    CHROMA_COLLECTION_NAME,
    COURSE_SYLLABUS_CSV,
    COURSES_CSV,
    DATA_DIR,
    DB_DIR,
    DB_PATH,
    EMBEDDING_MODEL,
    JOB_KEYWORDS_CSV,
    REAL_COURSES_CSV,
    REAL_SEMESTER_OPEN_CSV,
    SEMESTER_OPEN_CSV,
    VECTORSTORE_DIR,
)
from db_utils import get_connection


SAMPLE_COURSES = [
    {
        "course_id": "CSE301",
        "course_name": "인공지능",
        "description": "탐색 알고리즘, 지식 표현, 확률적 추론, 기계학습의 기초를 배우며 AI 연구자가 문제를 모델링하고 실험을 설계하는 데 필요한 핵심 개념을 다룬다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "CSE402",
        "course_name": "딥러닝",
        "description": "신경망, 합성곱 신경망, 순환 신경망, Transformer 구조와 표현학습을 구현한다. 논문 기반 실습을 통해 AI 연구와 모델 성능 분석 역량을 기른다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "CSE421",
        "course_name": "자연어처리",
        "description": "토큰화, 임베딩, 문서 분류, 정보검색, 언어모델, RAG 파이프라인을 다루며 텍스트 데이터를 활용한 AI 서비스와 연구 방법을 학습한다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "CSE411",
        "course_name": "컴퓨터비전",
        "description": "이미지 분류, 객체 탐지, 특징 추출, 딥러닝 기반 시각 인식 모델을 다룬다. AI 연구자와 제품 개발자가 시각 데이터를 분석하는 데 필요한 실습을 포함한다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "STA310",
        "course_name": "확률과 통계",
        "description": "확률분포, 추정, 가설검정, 회귀의 기초를 배우며 데이터 분석가, AI 연구자, 퀀트 직무에 필요한 통계적 사고와 불확실성 해석 능력을 기른다.",
        "credit": 3,
        "department": "통계학과",
    },
    {
        "course_id": "DS201",
        "course_name": "데이터 분석 입문",
        "description": "Python, pandas, 데이터 정제, 탐색적 데이터 분석, 시각화, 리포팅을 실습한다. 데이터 분석가가 비즈니스 질문을 데이터 문제로 바꾸는 방법을 배운다.",
        "credit": 3,
        "department": "데이터사이언스학부",
    },
    {
        "course_id": "DS302",
        "course_name": "머신러닝",
        "description": "지도학습, 비지도학습, 모델 평가, 교차검증, feature engineering을 다룬다. 데이터 분석가와 AI 연구자가 예측 모델을 만들고 성능을 해석하는 수업이다.",
        "credit": 3,
        "department": "데이터사이언스학부",
    },
    {
        "course_id": "DS330",
        "course_name": "데이터 시각화",
        "description": "시각 인코딩, 대시보드 설계, matplotlib, seaborn, plotly를 활용해 분석 결과를 명확하게 전달한다. UX 디자이너와 데이터 분석가에게 유용하다.",
        "credit": 3,
        "department": "데이터사이언스학부",
    },
    {
        "course_id": "DS410",
        "course_name": "빅데이터 처리",
        "description": "대용량 로그 데이터, Spark, 분산 처리, 데이터 파이프라인, 배치 처리 개념을 학습한다. 데이터 분석가와 백엔드 개발자가 확장 가능한 분석 시스템을 이해한다.",
        "credit": 3,
        "department": "데이터사이언스학부",
    },
    {
        "course_id": "BIZ305",
        "course_name": "비즈니스 애널리틱스",
        "description": "고객 데이터, 매출 데이터, KPI, 실험 분석, 의사결정 모델을 활용해 비즈니스 문제를 해결한다. 데이터 분석가와 핀테크 직무에 필요한 해석 역량을 다룬다.",
        "credit": 3,
        "department": "경영학과",
    },
    {
        "course_id": "CSE220",
        "course_name": "자료구조",
        "description": "배열, 리스트, 스택, 큐, 트리, 그래프, 해시 테이블을 구현하고 시간복잡도를 분석한다. 소프트웨어 개발자와 백엔드 개발자의 기본 역량을 만든다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "CSE310",
        "course_name": "알고리즘",
        "description": "정렬, 탐색, 그래프 알고리즘, 동적 계획법, 복잡도 분석을 학습한다. 백엔드 개발자, AI 연구자, 퀀트가 효율적인 문제 해결 전략을 익히는 데 적합하다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "CSE331",
        "course_name": "데이터베이스",
        "description": "관계형 데이터베이스, SQL, 정규화, 트랜잭션, 인덱스, 쿼리 최적화를 다룬다. 백엔드 개발자와 데이터 분석가에게 필수적인 데이터 저장 기술을 배운다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "CSE350",
        "course_name": "소프트웨어공학",
        "description": "요구사항 분석, 설계 패턴, 테스트, 형상관리, 협업 개발 프로세스를 다룬다. 소프트웨어 개발자가 안정적인 서비스를 만드는 실무 방식을 학습한다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "CSE430",
        "course_name": "웹 백엔드 개발",
        "description": "REST API, 인증, 서버 아키텍처, ORM, 캐싱, 배포를 실습한다. 백엔드 및 소프트웨어 개발자가 실제 웹 서비스를 구현하는 데 필요한 내용을 포함한다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "FIN301",
        "course_name": "금융공학",
        "description": "파생상품, 옵션 가격결정, 포트폴리오 이론, 위험 관리 모델을 배운다. 금융권, 핀테크, 퀀트 직무에서 수리적 금융 모델을 이해하는 데 중요하다.",
        "credit": 3,
        "department": "금융학과",
    },
    {
        "course_id": "FIN330",
        "course_name": "핀테크 서비스 기획",
        "description": "전자결제, 오픈뱅킹, 금융 API, 보안, 사용자 인증, 규제 환경을 다룬다. 핀테크 서비스와 금융권 디지털 전환을 이해하는 수업이다.",
        "credit": 3,
        "department": "금융학과",
    },
    {
        "course_id": "FIN410",
        "course_name": "퀀트 투자 전략",
        "description": "팩터 모델, 백테스팅, 시계열 데이터, 포트폴리오 최적화, 리스크 지표를 Python으로 실습한다. 퀀트와 금융 데이터 분석 직무에 직접 연결된다.",
        "credit": 3,
        "department": "금융학과",
    },
    {
        "course_id": "ECO320",
        "course_name": "계량경제학",
        "description": "회귀분석, 인과추론, 패널 데이터, 시계열 분석을 통해 경제 및 금융 데이터를 해석한다. 데이터 분석가와 금융권 리서치 직무에 적합하다.",
        "credit": 3,
        "department": "경제학과",
    },
    {
        "course_id": "CSE440",
        "course_name": "클라우드 컴퓨팅",
        "description": "컨테이너, 마이크로서비스, 클라우드 배포, 서버리스, 모니터링을 다룬다. 백엔드 개발자와 핀테크 서비스 개발자가 확장 가능한 시스템을 설계하는 데 필요하다.",
        "credit": 3,
        "department": "컴퓨터공학과",
    },
    {
        "course_id": "DES210",
        "course_name": "UX 디자인 기초",
        "description": "사용자 조사, 페르소나, 여정지도, 정보구조, 인터랙션 설계를 학습한다. UX 디자이너가 사용자의 문제를 정의하고 해결안을 설계하는 기본 수업이다.",
        "credit": 3,
        "department": "디자인학부",
    },
    {
        "course_id": "DES310",
        "course_name": "사용자 리서치",
        "description": "인터뷰, 설문, 사용성 테스트, 정성 데이터 분석, 리서치 리포트 작성을 실습한다. UX 디자이너와 프로덕트 팀이 근거 기반 의사결정을 하는 데 필요하다.",
        "credit": 3,
        "department": "디자인학부",
    },
    {
        "course_id": "DES330",
        "course_name": "인터랙션 디자인",
        "description": "모바일 앱, 웹 서비스, 프로토타이핑, 마이크로인터랙션, 접근성을 다룬다. UX 디자이너가 사용 흐름과 화면 전환을 설계하는 역량을 기른다.",
        "credit": 3,
        "department": "디자인학부",
    },
    {
        "course_id": "DES410",
        "course_name": "서비스 디자인",
        "description": "서비스 블루프린트, 고객 경험, 터치포인트, 운영 프로세스를 분석한다. UX 디자이너가 복잡한 서비스 경험을 구조화하는 데 유용하다.",
        "credit": 3,
        "department": "디자인학부",
    },
    {
        "course_id": "HCI401",
        "course_name": "HCI와 사용성 평가",
        "description": "인간-컴퓨터 상호작용, 인지 부하, 실험 설계, 사용성 평가, 접근성 원칙을 배운다. UX 디자이너와 AI 서비스 기획자에게 중요한 평가 방법을 제공한다.",
        "credit": 3,
        "department": "융합전공",
    },
]

JOB_KEYWORDS = {
    "AI 연구자": ["AI", "인공지능", "기계학습", "딥러닝", "머신러닝", "자연어처리", "컴퓨터비전", "논문", "모델 평가"],
    "데이터 분석가": ["데이터 분석", "통계", "시각화", "Python", "pandas", "머신러닝", "비즈니스 애널리틱스", "SQL"],
    "백엔드 / 소프트웨어 개발자": ["백엔드", "소프트웨어", "자료구조", "알고리즘", "데이터베이스", "API", "클라우드"],
    "금융권 / 핀테크 / 퀀트": ["금융", "핀테크", "퀀트", "포트폴리오", "시계열", "리스크", "백테스팅"],
    "UX 디자이너": ["UX", "사용자 리서치", "인터랙션", "사용성", "프로토타이핑", "서비스 디자인", "접근성"],
}


def ensure_directories() -> None:
    """Create required project directories."""
    for directory in [DATA_DIR, DB_DIR, VECTORSTORE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write dictionaries to a CSV file with UTF-8 encoding."""
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def create_sample_csvs() -> None:
    """Create sample course, semester-open, and job-keyword CSV files."""
    ensure_directories()

    semester_rows = []
    for index, course in enumerate(SAMPLE_COURSES):
        # Most courses are open in 2026-1; a few closed rows keep filtering realistic.
        semester_rows.append(
            {
                "course_id": course["course_id"],
                "semester": "2026-1",
                "is_open": "1" if index not in {3, 18} else "0",
            }
        )
        semester_rows.append(
            {
                "course_id": course["course_id"],
                "semester": "2026-2",
                "is_open": "1" if index % 2 == 0 else "0",
            }
        )

    keyword_rows = [
        {"job": job, "keyword": keyword}
        for job, keywords in JOB_KEYWORDS.items()
        for keyword in keywords
    ]

    write_csv(COURSES_CSV, SAMPLE_COURSES, ["course_id", "course_name", "description", "credit", "department"])
    write_csv(SEMESTER_OPEN_CSV, semester_rows, ["course_id", "semester", "is_open"])
    write_csv(JOB_KEYWORDS_CSV, keyword_rows, ["job", "keyword"])


def recreate_database(use_real_data: bool = False) -> None:
    """Create a fresh SQLite database from CSV files."""
    courses_csv = REAL_COURSES_CSV if use_real_data else COURSES_CSV
    semester_open_csv = REAL_SEMESTER_OPEN_CSV if use_real_data else SEMESTER_OPEN_CSV

    if use_real_data and (not courses_csv.exists() or not semester_open_csv.exists()):
        raise FileNotFoundError(
            "실제 수강편람 CSV가 없습니다. "
            "`data/real_courses_2026_1.csv`와 `data/real_semester_open_2026_1.csv`를 확인하세요."
        )

    if not use_real_data and (
        not COURSES_CSV.exists() or not SEMESTER_OPEN_CSV.exists() or not JOB_KEYWORDS_CSV.exists()
    ):
        create_sample_csvs()

    DB_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with get_connection(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                description TEXT NOT NULL,
                credit INTEGER NOT NULL,
                department TEXT NOT NULL
            );

            CREATE TABLE semester_open (
                course_id TEXT NOT NULL,
                semester TEXT NOT NULL,
                is_open BOOLEAN NOT NULL,
                PRIMARY KEY (course_id, semester)
            );

            CREATE TABLE job_keywords (
                job TEXT NOT NULL,
                keyword TEXT NOT NULL,
                PRIMARY KEY (job, keyword)
            );

            CREATE TABLE course_syllabus (
                course_id TEXT NOT NULL,
                section TEXT NOT NULL,
                week INTEGER,
                title TEXT NOT NULL,
                content TEXT,
                PRIMARY KEY (course_id, section, week, title)
            );
            """
        )

        with courses_csv.open("r", encoding="utf-8") as file:
            rows = csv.DictReader(file)
            cursor.executemany(
                """
                INSERT INTO courses (course_id, course_name, description, credit, department)
                VALUES (:course_id, :course_name, :description, :credit, :department)
                """,
                rows,
            )

        with semester_open_csv.open("r", encoding="utf-8") as file:
            rows = [
                {
                    "course_id": row["course_id"],
                    "semester": row["semester"],
                    "is_open": int(row["is_open"]),
                }
                for row in csv.DictReader(file)
            ]
            cursor.executemany(
                """
                INSERT INTO semester_open (course_id, semester, is_open)
                VALUES (:course_id, :semester, :is_open)
                """,
                rows,
            )

        with JOB_KEYWORDS_CSV.open("r", encoding="utf-8") as file:
            rows = csv.DictReader(file)
            cursor.executemany(
                """
                INSERT INTO job_keywords (job, keyword)
                VALUES (:job, :keyword)
                """,
                rows,
            )

        if COURSE_SYLLABUS_CSV.exists():
            with COURSE_SYLLABUS_CSV.open("r", encoding="utf-8") as file:
                rows = []
                for row in csv.DictReader(file):
                    rows.append(
                        {
                            "course_id": row["course_id"],
                            "section": row["section"],
                            "week": int(row["week"]) if row["week"] else None,
                            "title": row["title"],
                            "content": row["content"],
                        }
                    )
                cursor.executemany(
                    """
                    INSERT INTO course_syllabus (course_id, section, week, title, content)
                    VALUES (:course_id, :section, :week, :title, :content)
                    """,
                    rows,
                )

        connection.commit()


def require_openai_api_key() -> None:
    """Fail early when OpenAI API key is missing."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다. "
            "예: export OPENAI_API_KEY='sk-...' 실행 후 다시 시도하세요."
        )


def build_vectorstore(reset: bool = True) -> None:
    """Embed course descriptions and persist them to ChromaDB."""
    require_openai_api_key()

    from langchain_chroma import Chroma
    from langchain_core.documents import Document
    from langchain_openai import OpenAIEmbeddings

    if not DB_PATH.exists():
        recreate_database()

    if reset and VECTORSTORE_DIR.exists():
        shutil.rmtree(VECTORSTORE_DIR)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT course_id, course_name, description, credit, department
            FROM courses
            ORDER BY course_id
            """
        ).fetchall()

    documents = [
        Document(
            page_content=row["description"],
            metadata={
                "course_id": row["course_id"],
                "course_name": row["course_name"],
                "department": row["department"],
                "credit": row["credit"],
            },
        )
        for row in rows
    ]

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=str(VECTORSTORE_DIR),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Course RAG data pipeline")
    parser.add_argument("--sample-data", action="store_true", help="Create sample CSV files only")
    parser.add_argument("--db", action="store_true", help="Recreate SQLite DB from CSV files")
    parser.add_argument("--vectorstore", action="store_true", help="Create ChromaDB vectorstore")
    parser.add_argument("--all", action="store_true", help="Run sample data, DB, and vectorstore steps")
    parser.add_argument("--real-data", action="store_true", help="Use real 2026-1 curriculum CSV files for DB")
    args = parser.parse_args()

    if args.all or args.sample_data:
        create_sample_csvs()
        print(f"Sample CSV files created in {DATA_DIR}")

    if args.all or args.db:
        recreate_database(use_real_data=args.real_data)
        source_label = "real 2026-1 CSV" if args.real_data else "sample CSV"
        print(f"SQLite DB created at {DB_PATH} from {source_label}")

    if args.all or args.vectorstore:
        try:
            build_vectorstore(reset=True)
            print(f"ChromaDB vectorstore created at {VECTORSTORE_DIR}")
        except RuntimeError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)

    if not any([args.all, args.sample_data, args.db, args.vectorstore]):
        create_sample_csvs()
        print(f"Sample CSV files created in {DATA_DIR}")
        recreate_database(use_real_data=args.real_data)
        source_label = "real 2026-1 CSV" if args.real_data else "sample CSV"
        print(f"SQLite DB created at {DB_PATH} from {source_label}")
        print("Next step: python rag_pipeline.py --build-vectorstore")


if __name__ == "__main__":
    main()
