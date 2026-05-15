"""RAG pipeline for job-based course recommendation.

This module can also be used from the command line:
    python rag_pipeline.py --build-vectorstore
    python rag_pipeline.py --demo
"""

import argparse
import json
import os
import sys
from typing import Any

from config import (
    CHROMA_COLLECTION_NAME,
    DB_PATH,
    DEFAULT_RECOMMEND_TOP_N,
    DEFAULT_SEARCH_TOP_K,
    DEFAULT_SEMESTER,
    EMBEDDING_MODEL,
    LLM_MODEL,
    MIN_RECOMMEND_TOP_N,
    VECTORSTORE_DIR,
)
from db_utils import fetch_all, is_course_open


def require_openai_api_key() -> None:
    """Raise a helpful error when the API key is missing."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다. "
            "임베딩 검색과 GPT 추천 이유 생성을 위해 API Key가 필요합니다."
        )


def get_keywords_by_job(job: str) -> list[str]:
    """Return keywords mapped to the selected job from SQLite."""
    rows = fetch_all(
        "SELECT keyword FROM job_keywords WHERE job = ? ORDER BY keyword",
        (job,),
        DB_PATH,
    )
    return [row["keyword"] for row in rows]


def is_demo_mode() -> bool:
    """Return True when local demo mode is enabled.

    Demo mode lets beginners inspect the UI and recommendation cards before
    connecting billing/API credentials. It does not use ChromaDB or OpenAI.
    """
    return os.getenv("DEMO_MODE", "").lower() in {"1", "true", "yes", "y"}


def get_vectorstore():
    """Load the persisted ChromaDB collection."""
    require_openai_api_key()
    if not VECTORSTORE_DIR.exists() or not any(VECTORSTORE_DIR.iterdir()):
        raise FileNotFoundError(
            "ChromaDB 벡터 저장소가 없습니다. 먼저 `python data_pipeline.py --vectorstore`를 실행하세요."
        )

    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
    )


def search_relevant_courses(job: str, top_k: int = DEFAULT_SEARCH_TOP_K) -> list[dict[str, Any]]:
    """Search ChromaDB using the job name and mapped keywords."""
    keywords = get_keywords_by_job(job)
    if not keywords:
        raise ValueError(f"지원하지 않는 직업 카테고리입니다: {job}")

    if is_demo_mode():
        return search_relevant_courses_demo(job, top_k=top_k)

    query = f"{job} 관련 수업 추천: " + ", ".join(keywords)
    vectorstore = get_vectorstore()
    docs_with_scores = vectorstore.similarity_search_with_score(query, k=top_k)

    results = []
    for document, score in docs_with_scores:
        results.append(
            {
                "course_id": document.metadata.get("course_id"),
                "course_name": document.metadata.get("course_name"),
                "department": document.metadata.get("department"),
                "credit": document.metadata.get("credit"),
                "description": document.page_content,
                "score": score,
                "matched_keywords": [
                    keyword for keyword in keywords if keyword.lower() in document.page_content.lower()
                ],
            }
        )
    return results


def search_relevant_courses_demo(job: str, top_k: int = DEFAULT_SEARCH_TOP_K) -> list[dict[str, Any]]:
    """Search courses with simple keyword matching for API-free local testing."""
    keywords = get_keywords_by_job(job)
    rows = fetch_all(
        """
        SELECT course_id, course_name, description, credit, department
        FROM courses
        ORDER BY course_id
        """,
        (),
        DB_PATH,
    )

    results = []
    for row in rows:
        searchable_text = f"{row['course_name']} {row['department']} {row['description']}".lower()
        matched_keywords = [keyword for keyword in keywords if keyword.lower() in searchable_text]
        if matched_keywords:
            results.append(
                {
                    "course_id": row["course_id"],
                    "course_name": row["course_name"],
                    "department": row["department"],
                    "credit": row["credit"],
                    "description": row["description"],
                    "score": -len(matched_keywords),
                    "matched_keywords": matched_keywords,
                }
            )

    results.sort(key=lambda item: (item["score"], item["course_id"]))
    return results[:top_k]


def filter_open_courses(results: list[dict[str, Any]], semester: str = DEFAULT_SEMESTER) -> list[dict[str, Any]]:
    """Keep only courses marked as open in the selected semester."""
    return [
        result
        for result in results
        if result.get("course_id") and is_course_open(result["course_id"], semester, DB_PATH)
    ]


def get_syllabus_by_course(course_id: str) -> dict[str, Any] | None:
    """Return syllabus information for a course if it exists in SQLite."""
    rows = fetch_all(
        """
        SELECT section, week, title, content
        FROM course_syllabus
        WHERE course_id = ?
        ORDER BY
            CASE section
                WHEN 'overview' THEN 1
                WHEN 'objective' THEN 2
                WHEN 'topics' THEN 3
                WHEN 'prerequisite' THEN 4
                WHEN 'textbook' THEN 5
                WHEN 'reference' THEN 6
                WHEN 'evaluation' THEN 7
                WHEN 'week' THEN 8
                ELSE 9
            END,
            week
        """,
        (course_id,),
        DB_PATH,
    )
    if not rows:
        return None

    details = []
    weekly_plan = []
    for row in rows:
        item = {
            "section": row["section"],
            "week": row["week"],
            "title": row["title"],
            "content": row["content"] or "",
        }
        if row["section"] == "week":
            weekly_plan.append(item)
        else:
            details.append(item)

    return {
        "course_id": course_id,
        "details": details,
        "weekly_plan": weekly_plan,
    }


def _fallback_summary(description: str, max_chars: int = 120) -> str:
    """Create a short local summary when LLM output is unavailable."""
    return description if len(description) <= max_chars else description[:max_chars].rstrip() + "..."


def generate_course_reason(job: str, course: dict[str, Any], keywords: list[str]) -> dict[str, str]:
    """Generate Korean recommendation reason and evidence summary using GPT-4o-mini."""
    if is_demo_mode():
        matched = course.get("matched_keywords") or [
            keyword for keyword in keywords if keyword.lower() in course["description"].lower()
        ]
        keyword_text = ", ".join(matched[:3]) if matched else "직업 관련 키워드"
        return {
            "reason": (
                f"이 수업은 수강편람 설명에서 {keyword_text}와 연결되는 내용을 다룹니다. "
                f"{job} 진로에 필요한 기초 개념이나 실무 역량을 확인하는 데 도움이 됩니다."
            ),
            "summary": _fallback_summary(course["description"]),
        }

    require_openai_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

    prompt = f"""
당신은 대학 수강 추천 도우미입니다.
반드시 아래 수강편람 description에 근거해서만 답하세요.
description에 없는 선수과목, 평가 방식, 교수명, 시간표, 난이도는 추측하지 마세요.
확인할 수 없는 내용은 "수강편람 정보만으로는 확인하기 어렵습니다"라고 답하세요.

[직업 카테고리]
{job}

[관련 키워드]
{", ".join(keywords)}

[수업 정보]
과목명: {course["course_name"]}
학과: {course["department"]}
학점: {course["credit"]}
description: {course["description"]}

아래 형식으로 한국어 JSON만 출력하세요.
{{
  "reason": "이 직업과 연결되는 추천 이유 2문장",
  "summary": "수강편람 description 근거 요약 1문장"
}}
"""
    response = llm.invoke(prompt)

    # Avoid adding another dependency for simple parsing fallback. The response is
    # requested as JSON, but if it is malformed we still return useful text.
    import json

    try:
        parsed = json.loads(response.content)
        return {
            "reason": parsed.get("reason", "수강편람 정보만으로는 확인하기 어렵습니다"),
            "summary": parsed.get("summary", _fallback_summary(course["description"])),
        }
    except json.JSONDecodeError:
        return {
            "reason": response.content.strip(),
            "summary": _fallback_summary(course["description"]),
        }


def recommend_courses(
    job: str,
    semester: str = DEFAULT_SEMESTER,
    top_n: int = DEFAULT_RECOMMEND_TOP_N,
) -> list[dict[str, Any]]:
    """Return top open courses with reasons, keywords, and evidence summaries."""
    if top_n < MIN_RECOMMEND_TOP_N or top_n > DEFAULT_RECOMMEND_TOP_N:
        raise ValueError(f"top_n은 {MIN_RECOMMEND_TOP_N}~{DEFAULT_RECOMMEND_TOP_N} 사이여야 합니다.")

    keywords = get_keywords_by_job(job)
    search_results = search_relevant_courses(job, top_k=max(DEFAULT_SEARCH_TOP_K, top_n * 2))
    open_courses = filter_open_courses(search_results, semester=semester)

    recommendations = []
    for course in open_courses[:top_n]:
        llm_fields = generate_course_reason(job, course, keywords)
        related_keywords = course["matched_keywords"] or [
            keyword for keyword in keywords if keyword.lower() in course["description"].lower()
        ]
        recommendations.append(
            {
                "course_id": course["course_id"],
                "course_name": course["course_name"],
                "department": course["department"],
                "credit": course["credit"],
                "recommendation_reason": llm_fields["reason"],
                "related_keywords": related_keywords,
                "description_summary": llm_fields["summary"],
                "source_description": course["description"],
            }
        )

    if len(recommendations) < MIN_RECOMMEND_TOP_N:
        raise RuntimeError(
            f"{semester} 학기에 추천 가능한 개설 수업이 {MIN_RECOMMEND_TOP_N}개 미만입니다. "
            "샘플 데이터 또는 학기 값을 확인하세요."
        )

    return recommendations


def answer_followup_question(question: str, recommendations: list[dict[str, Any]]) -> str:
    """Answer an extra question using only the current recommendation context."""
    if not recommendations:
        return "먼저 추천 수업을 조회해 주세요."

    if is_demo_mode():
        restricted_topics = ["선수", "교수", "시간표", "난이도", "평가", "시험", "과제"]
        if any(topic in question for topic in restricted_topics):
            return "수강편람 정보만으로는 확인하기 어렵습니다"

        names = ", ".join(item["course_name"] for item in recommendations)
        return (
            f"현재 추천된 수업 context 기준으로는 {names}를 비교할 수 있습니다. "
            "더 구체적인 판단은 카드에 표시된 수업 설명 요약을 근거로 확인해 주세요."
        )

    require_openai_api_key()
    from langchain_openai import ChatOpenAI

    context_lines = []
    for item in recommendations:
        context_lines.append(
            f"- {item['course_name']}({item['course_id']}): "
            f"{item['department']}, {item['credit']}학점, "
            f"description: {item['source_description']}"
        )
    context = "\n".join(context_lines)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = f"""
당신은 수강 추천 챗봇입니다.
아래 context 안에 있는 현재 추천 수업 정보만 사용해서 답하세요.
context에 없는 내용은 추측하지 말고 "수강편람 정보만으로는 확인하기 어렵습니다"라고 답하세요.
답변은 한국어로 간결하게 작성하세요.

[현재 추천 수업 context]
{context}

[사용자 질문]
{question}
"""
    return llm.invoke(prompt).content.strip()


def build_vectorstore_from_cli() -> None:
    """Build ChromaDB by reusing the data pipeline function."""
    from data_pipeline import build_vectorstore

    build_vectorstore(reset=True)
    print(f"ChromaDB vectorstore created at {VECTORSTORE_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Course recommendation RAG pipeline")
    parser.add_argument("--build-vectorstore", action="store_true", help="Create ChromaDB vectorstore")
    parser.add_argument("--demo", action="store_true", help="Run a local API-free recommendation smoke test")
    parser.add_argument("--job", default="AI 연구자", help="Job category for --demo")
    parser.add_argument("--semester", default=DEFAULT_SEMESTER, help="Semester for --demo")
    args = parser.parse_args()

    try:
        if args.build_vectorstore:
            build_vectorstore_from_cli()
            return

        if args.demo:
            os.environ["DEMO_MODE"] = "1"
            items = recommend_courses(args.job, semester=args.semester, top_n=3)
            print(json.dumps(items, ensure_ascii=False, indent=2))
            return

        parser.print_help()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
