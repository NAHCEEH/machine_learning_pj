"""Project-wide configuration values.

All paths are defined relative to this file so the project can be run from
any working directory.
"""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
VECTORSTORE_DIR = BASE_DIR / "vectorstore" / "chroma"
LOGS_DIR = BASE_DIR / "logs"
EVALUATION_DIR = BASE_DIR / "evaluation"

COURSES_CSV = DATA_DIR / "sample_courses.csv"
SEMESTER_OPEN_CSV = DATA_DIR / "sample_semester_open.csv"
JOB_KEYWORDS_CSV = DATA_DIR / "job_keywords.csv"
COURSE_SYLLABUS_CSV = DATA_DIR / "course_syllabus.csv"
REAL_COURSES_CSV = DATA_DIR / "real_courses_2026_1.csv"
REAL_SEMESTER_OPEN_CSV = DATA_DIR / "real_semester_open_2026_1.csv"
DB_PATH = DB_DIR / "courses.db"

DEFAULT_SEMESTER = "2026-1"
SUPPORTED_JOBS = [
    "AI 연구자",
    "데이터 분석가",
    "백엔드 / 소프트웨어 개발자",
    "금융권 / 핀테크 / 퀀트",
    "UX 디자이너",
]

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"
CHROMA_COLLECTION_NAME = "course_descriptions"

DEFAULT_SEARCH_TOP_K = 10
DEFAULT_RECOMMEND_TOP_N = 5
MIN_RECOMMEND_TOP_N = 3
