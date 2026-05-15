"""Enhanced Streamlit UI for the job-based course recommendation RAG chatbot."""

import json
import os
from datetime import datetime

import streamlit as st

from config import DEFAULT_SEMESTER, SUPPORTED_JOBS
from rag_pipeline import answer_followup_question, get_syllabus_by_course, recommend_courses

# ── 페이지 설정 ────────────────────────────────────────────────
st.set_page_config(
    page_title="수강 추천 챗봇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 커스텀 CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    /* 전체 폰트 */
    html, body, [class*="css"] { font-family: 'Pretendard', 'Noto Sans KR', sans-serif; }

    /* 메인 타이틀 */
    .main-title {
        font-size: 2rem; font-weight: 800; color: #1a237e;
        letter-spacing: -0.5px; margin-bottom: 0;
    }
    .main-subtitle { font-size: 0.95rem; color: #666; margin-top: 4px; }

    /* 수업 카드 */
    .course-card {
        border: 1.5px solid #e3e8f0; border-radius: 14px;
        padding: 20px 22px; margin-bottom: 14px;
        background: linear-gradient(135deg, #ffffff 0%, #f8faff 100%);
        box-shadow: 0 2px 8px rgba(26,35,126,0.06);
        transition: box-shadow 0.2s;
    }
    .course-card:hover { box-shadow: 0 6px 20px rgba(26,35,126,0.12); }
    .course-rank {
        display: inline-block; background: #1a237e; color: white;
        border-radius: 50%; width: 28px; height: 28px;
        text-align: center; line-height: 28px; font-weight: 700;
        font-size: 0.85rem; margin-right: 8px;
    }
    .course-name { font-size: 1.1rem; font-weight: 700; color: #1a237e; display: inline; }
    .course-meta { color: #888; font-size: 0.82rem; margin: 6px 0 12px; }

    /* 키워드 태그 */
    .keyword-tag {
        display: inline-block; background: #e8eaf6; color: #3949ab;
        border-radius: 20px; padding: 3px 12px; font-size: 0.78rem;
        font-weight: 600; margin: 3px 3px 3px 0;
    }

    /* 섹션 라벨 */
    .section-label {
        font-size: 0.78rem; font-weight: 700; color: #3949ab;
        text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px;
    }

    /* 메트릭 카드 */
    .metric-box {
        background: #f0f4ff; border-radius: 12px; padding: 14px 18px;
        text-align: center; border: 1px solid #dde3f8;
    }
    .metric-value { font-size: 1.6rem; font-weight: 800; color: #1a237e; }
    .metric-label { font-size: 0.78rem; color: #666; margin-top: 2px; }

    /* 채팅 버블 */
    .chat-user {
        background: #1a237e; color: white; border-radius: 18px 18px 4px 18px;
        padding: 10px 16px; margin: 8px 0 4px auto;
        max-width: 75%; font-size: 0.92rem; display: inline-block; float: right; clear: both;
    }
    .chat-bot {
        background: #f0f4ff; color: #1a1a1a; border-radius: 18px 18px 18px 4px;
        padding: 10px 16px; margin: 4px auto 8px 0;
        max-width: 85%; font-size: 0.92rem; display: inline-block; float: left; clear: both;
    }
    .chat-time { font-size: 0.7rem; color: #aaa; margin: 2px 4px; clear: both; }
    .chat-wrap { overflow: hidden; margin-bottom: 4px; }

    /* 북마크 배지 */
    .bookmark-badge {
        background: #fff3e0; color: #e65100; border: 1px solid #ffcc80;
        border-radius: 20px; padding: 2px 10px; font-size: 0.75rem; font-weight: 600;
    }

    /* 탭 스타일 보정 */
    .stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 0.92rem; }

    /* 비교 모드 컬럼 헤더 */
    .compare-header {
        background: linear-gradient(135deg, #1a237e, #3949ab);
        color: white; border-radius: 10px; padding: 12px 16px;
        text-align: center; font-weight: 700; font-size: 1rem; margin-bottom: 12px;
    }

    /* 사이드바 */
    .sidebar-section { margin-bottom: 16px; }
    .sidebar-title { font-size: 0.78rem; font-weight: 700; color: #3949ab; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.6px; }
</style>
""", unsafe_allow_html=True)


# ── 세션 상태 초기화 ───────────────────────────────────────────
def init_session():
    defaults = {
        "recommendations": [],
        "compare_recs_a": [],
        "compare_recs_b": [],
        "chat_history": [],           # [{"role": "user"|"bot", "text": str, "time": str}]
        "bookmarks": [],              # [course dict]
        "last_job": "",
        "history_log": [],            # [{"job": str, "time": str, "count": int}]
        "demo_mode_enabled": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ── 헬퍼 함수들 ───────────────────────────────────────────────
def keyword_tags_html(keywords: list[str]) -> str:
    if not keywords:
        return "<span style='color:#aaa;font-size:0.8rem'>키워드 없음</span>"
    return " ".join(f'<span class="keyword-tag">{kw}</span>' for kw in keywords)


def is_bookmarked(course_id: str) -> bool:
    return any(b["course_id"] == course_id for b in st.session_state.bookmarks)


def toggle_bookmark(item: dict):
    if is_bookmarked(item["course_id"]):
        st.session_state.bookmarks = [
            b for b in st.session_state.bookmarks if b["course_id"] != item["course_id"]
        ]
    else:
        st.session_state.bookmarks.append(item)


def render_course_card(item: dict, index: int, show_bookmark_btn: bool = True):
    """수업 카드 렌더링 (공통)"""
    bookmarked = is_bookmarked(item["course_id"])
    bm_label = "저장됨" if bookmarked else "저장"

    col_main, col_bm = st.columns([10, 1.5])
    with col_main:
        st.markdown(
            f'<div class="course-card">'
            f'<span class="course-rank">{index}</span>'
            f'<span class="course-name">{item["course_name"]}</span><br>'
            f'<div class="course-meta">'
            f'{item["course_id"]} &nbsp;|&nbsp; {item["department"]} &nbsp;|&nbsp; {item["credit"]}학점'
            f'</div>'
            f'<div class="section-label">추천 이유</div>'
            f'<div style="font-size:0.9rem;color:#333;margin-bottom:12px">{item["recommendation_reason"]}</div>'
            f'<div class="section-label">관련 키워드</div>'
            f'<div style="margin-bottom:10px">{keyword_tags_html(item["related_keywords"])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_bm:
        if show_bookmark_btn:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            if st.button(bm_label, key=f"bm_{item['course_id']}_{index}"):
                toggle_bookmark(item)
                st.rerun()

    with st.expander(" 수업 설명 자세히 보기"):
        st.markdown(item.get("description_summary", "설명 없음"))

    syllabus = get_syllabus_by_course(item["course_id"])
    if syllabus:
        with st.expander("강의계획서 보기"):
            section_labels = {
                "overview": "교과목개요",
                "objective": "수업목표",
                "topics": "주요주제",
                "prerequisite": "선수과목 안내",
                "textbook": "교재",
                "reference": "부교재",
                "evaluation": "평가항목",
            }

            for detail in syllabus["details"]:
                label = section_labels.get(detail["section"], detail["title"])
                st.markdown(f"**{label}**")
                st.write(detail["content"] or detail["title"])

            if syllabus["weekly_plan"]:
                st.markdown("**주별 강의계획**")
                st.dataframe(
                    [
                        {
                            "주차": row["week"],
                            "주제": row["title"],
                            "활동사항": row["content"],
                        }
                        for row in syllabus["weekly_plan"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )


def make_csv(recs: list[dict]) -> str:
    if not recs:
        return ""
    header = "순위,수업코드,수업명,학과,학점,추천이유,관련키워드\n"
    rows = []
    for i, r in enumerate(recs, 1):
        kws = " / ".join(r.get("related_keywords", []))
        reason = r["recommendation_reason"].replace(",", " ").replace("\n", " ")
        rows.append(f'{i},{r["course_id"]},{r["course_name"]},{r["department"]},{r["credit"]},"{reason}",{kws}')
    return header + "\n".join(rows)


def apply_demo_mode_setting() -> None:
    """Apply the sidebar demo-mode setting before calling the RAG pipeline."""
    if st.session_state.get("demo_mode_enabled", False):
        os.environ["DEMO_MODE"] = "1"
    else:
        os.environ.pop("DEMO_MODE", None)


# ── 사이드바 ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 수강 추천 챗봇")
    st.markdown("---")

    st.markdown('<div class="sidebar-title">추천 설정</div>', unsafe_allow_html=True)
    selected_job = st.selectbox("희망 직업", SUPPORTED_JOBS, label_visibility="collapsed")
    semester = st.text_input("학기", value=DEFAULT_SEMESTER)
    top_n = st.slider("추천 수업 수", min_value=3, max_value=5, value=5)
    st.toggle(
        "API 없이 데모 모드",
        key="demo_mode_enabled",
        help="OpenAI API와 ChromaDB 없이 SQLite 샘플 데이터의 키워드 매칭으로 화면을 먼저 확인합니다.",
    )
    apply_demo_mode_setting()

    if st.button("🔍 수업 추천받기", type="primary", use_container_width=True):
        with st.spinner("수강편람을 검색하는 중..."):
            try:
                result = recommend_courses(selected_job, semester=semester, top_n=top_n)
                st.session_state.recommendations = result
                st.session_state.last_job = selected_job
                st.session_state.chat_history = []  # 추천 바뀌면 Q&A 초기화
                st.session_state.history_log.insert(0, {
                    "job": selected_job,
                    "time": datetime.now().strftime("%m/%d %H:%M"),
                    "count": len(result),
                })
            except Exception as e:
                st.error(str(e))

    st.markdown("---")

    # 북마크 요약
    st.markdown('<div class="sidebar-title">⭐ 저장된 수업</div>', unsafe_allow_html=True)
    if st.session_state.bookmarks:
        for bm in st.session_state.bookmarks:
            st.markdown(f"- **{bm['course_name']}** `{bm['course_id']}`")
        if st.button("저장 목록 초기화", use_container_width=True):
            st.session_state.bookmarks = []
            st.rerun()
    else:
        st.caption("수업 카드의 ☆ 버튼으로 저장하세요.")

    st.markdown("---")

    # 추천 히스토리
    st.markdown('<div class="sidebar-title">최근 조회 이력</div>', unsafe_allow_html=True)
    if st.session_state.history_log:
        for log in st.session_state.history_log[:5]:
            st.caption(f"**{log['job']}** ({log['count']}개) — {log['time']}")
    else:
        st.caption("아직 조회 이력이 없습니다.")


# ── 메인 콘텐츠 ───────────────────────────────────────────────
st.markdown(
    '<div class="main-title">직업 기반 수강 추천 챗봇</div>'
    '<div class="main-subtitle">원하는 직업을 선택하면 이번 학기 개설 수업 중 가장 관련 있는 강의를 추천해드립니다.</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# ── 메트릭 대시보드 ────────────────────────────────────────────
recs = st.session_state.recommendations
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="metric-box"><div class="metric-value">{len(recs)}</div>'
        f'<div class="metric-label">추천된 수업</div></div>', unsafe_allow_html=True)
with m2:
    departments = list(set(r["department"] for r in recs)) if recs else []
    st.markdown(
        f'<div class="metric-box"><div class="metric-value">{len(departments)}</div>'
        f'<div class="metric-label">관련 학과</div></div>', unsafe_allow_html=True)
with m3:
    total_credits = sum(r.get("credit", 0) for r in recs)
    st.markdown(
        f'<div class="metric-box"><div class="metric-value">{total_credits}</div>'
        f'<div class="metric-label">총 학점</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(
        f'<div class="metric-box"><div class="metric-value">{len(st.session_state.bookmarks)}</div>'
        f'<div class="metric-label">저장된 수업</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 탭 ────────────────────────────────────────────────────────
tab_rec, tab_compare, tab_qa, tab_bookmark = st.tabs([
    "추천 결과",
    "직업 비교",
    "추가 질문 (Q&A)",
    "저장된 수업",
])


# ── 탭 1: 추천 결과 ───────────────────────────────────────────
with tab_rec:
    if recs:
        job_label = st.session_state.last_job
        header_col, export_col = st.columns([7, 3])
        with header_col:
            st.subheader(f"'{job_label}' 추천 수업 ({len(recs)}개)")
        with export_col:
            csv_data = make_csv(recs)
            st.download_button(
                label="⬇ CSV로 내보내기",
                data=csv_data,
                file_name=f"추천_{job_label}_{semester}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # 학과 필터
        all_depts = ["전체"] + sorted(set(r["department"] for r in recs))
        dept_filter = st.selectbox("학과 필터", all_depts, key="dept_filter")
        filtered = recs if dept_filter == "전체" else [r for r in recs if r["department"] == dept_filter]

        st.markdown("---")
        for i, item in enumerate(filtered, start=1):
            render_course_card(item, i)
    else:
        st.info("사이드바에서 직업 카테고리를 선택하고 **수업 추천받기** 버튼을 눌러보세요.")


# ── 탭 2: 직업 비교 ───────────────────────────────────────────
with tab_compare:
    st.markdown("두 직업의 추천 수업을 나란히 비교합니다.")
    col_a, col_b = st.columns(2)

    with col_a:
        job_a = st.selectbox("직업 A", SUPPORTED_JOBS, key="job_a")
        if st.button("A 추천받기", key="btn_a", use_container_width=True):
            with st.spinner(f"{job_a} 수업 검색 중..."):
                try:
                    apply_demo_mode_setting()
                    st.session_state.compare_recs_a = recommend_courses(job_a, semester=semester, top_n=3)
                except Exception as e:
                    st.error(str(e))

    with col_b:
        job_b = st.selectbox("직업 B", SUPPORTED_JOBS, index=1, key="job_b")
        if st.button("B 추천받기", key="btn_b", use_container_width=True):
            with st.spinner(f"{job_b} 수업 검색 중..."):
                try:
                    apply_demo_mode_setting()
                    st.session_state.compare_recs_b = recommend_courses(job_b, semester=semester, top_n=3)
                except Exception as e:
                    st.error(str(e))

    st.markdown("---")
    res_a = st.session_state.compare_recs_a
    res_b = st.session_state.compare_recs_b

    if res_a or res_b:
        col_left, col_right = st.columns(2)
        with col_left:
            if res_a:
                st.markdown(f'<div class="compare-header">🅐 {job_a}</div>', unsafe_allow_html=True)
                for i, item in enumerate(res_a, 1):
                    st.markdown(
                        f'<div class="course-card">'
                        f'<span class="course-rank">{i}</span>'
                        f'<span class="course-name">{item["course_name"]}</span><br>'
                        f'<div class="course-meta">{item["course_id"]} | {item["department"]} | {item["credit"]}학점</div>'
                        f'<div style="font-size:0.85rem;color:#444">{item["recommendation_reason"]}</div>'
                        f'<div style="margin-top:8px">{keyword_tags_html(item["related_keywords"])}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        with col_right:
            if res_b:
                st.markdown(f'<div class="compare-header">🅑 {job_b}</div>', unsafe_allow_html=True)
                for i, item in enumerate(res_b, 1):
                    st.markdown(
                        f'<div class="course-card">'
                        f'<span class="course-rank">{i}</span>'
                        f'<span class="course-name">{item["course_name"]}</span><br>'
                        f'<div class="course-meta">{item["course_id"]} | {item["department"]} | {item["credit"]}학점</div>'
                        f'<div style="font-size:0.85rem;color:#444">{item["recommendation_reason"]}</div>'
                        f'<div style="margin-top:8px">{keyword_tags_html(item["related_keywords"])}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # 중복 수업 하이라이트
        if res_a and res_b:
            ids_a = {r["course_id"] for r in res_a}
            ids_b = {r["course_id"] for r in res_b}
            overlap = ids_a & ids_b
            if overlap:
                overlap_names = [r["course_name"] for r in res_a if r["course_id"] in overlap]
                st.success(f"두 직업 모두에 추천되는 수업: **{', '.join(overlap_names)}**")
            else:
                st.info("두 직업 간 겹치는 추천 수업이 없습니다.")
    else:
        st.info("A, B 직업을 각각 선택하고 추천을 받아보세요.")


# ── 탭 3: 추가 질문 Q&A ───────────────────────────────────────
with tab_qa:
    if not recs:
        st.info("먼저 추천 결과를 받은 후 추가 질문을 할 수 있습니다.")
    else:
        st.markdown(f"**'{st.session_state.last_job}'** 추천 수업 {len(recs)}개를 근거로 답변합니다.")

        # 빠른 질문 버튼
        st.markdown("**자주 묻는 질문**")
        quick_cols = st.columns(3)
        quick_questions = [
            "선수과목이 필요한 수업이 있나요?",
            "가장 입문자에게 적합한 수업은?",
            "총 몇 학점인가요?",
        ]
        for i, (col, q) in enumerate(zip(quick_cols, quick_questions)):
            with col:
                if st.button(q, key=f"quick_{i}", use_container_width=True):
                    with st.spinner("답변 생성 중..."):
                        try:
                            apply_demo_mode_setting()
                            ans = answer_followup_question(q, recs)
                            now = datetime.now().strftime("%H:%M")
                            st.session_state.chat_history.append({"role": "user", "text": q, "time": now})
                            st.session_state.chat_history.append({"role": "bot", "text": ans, "time": now})
                        except Exception as e:
                            st.error(str(e))
                    st.rerun()

        st.markdown("---")

        # 채팅 히스토리 출력
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="chat-wrap"><div class="chat-user">{msg["text"]}</div></div>'
                        f'<div class="chat-time" style="text-align:right">{msg["time"]}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="chat-wrap"><div class="chat-bot">{msg["text"]}</div></div>'
                        f'<div class="chat-time">{msg["time"]}</div>',
                        unsafe_allow_html=True,
                    )

        # 입력창
        st.markdown("<br>", unsafe_allow_html=True)
        q_col, btn_col = st.columns([8, 2])
        with q_col:
            user_q = st.text_input(
                "질문 입력",
                placeholder="예: 이 수업들 중 가장 취업에 도움이 되는 건?",
                label_visibility="collapsed",
                key="qa_input",
            )
        with btn_col:
            ask_btn = st.button("전송 ➤", type="primary", use_container_width=True)

        if ask_btn and user_q:
            with st.spinner("답변 생성 중..."):
                try:
                    apply_demo_mode_setting()
                    ans = answer_followup_question(user_q, recs)
                    now = datetime.now().strftime("%H:%M")
                    st.session_state.chat_history.append({"role": "user", "text": user_q, "time": now})
                    st.session_state.chat_history.append({"role": "bot", "text": ans, "time": now})
                except Exception as e:
                    st.error(str(e))
            st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑 대화 초기화", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()


# ── 탭 4: 저장된 수업 ─────────────────────────────────────────
with tab_bookmark:
    bookmarks = st.session_state.bookmarks
    if not bookmarks:
        st.info("추천 결과에서 ☆ 버튼을 눌러 관심 수업을 저장해보세요.")
    else:
        bm_header, bm_export = st.columns([7, 3])
        with bm_header:
            st.subheader(f"저장된 수업 ({len(bookmarks)}개)")
        with bm_export:
            bm_csv = make_csv(bookmarks)
            st.download_button(
                label="⬇ CSV로 내보내기",
                data=bm_csv,
                file_name="저장된_수업.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.markdown("---")
        for i, item in enumerate(bookmarks, 1):
            render_course_card(item, i, show_bookmark_btn=True)
