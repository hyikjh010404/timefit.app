import streamlit as st
import base64
import re
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# =========================
# 페이지 설정
# =========================
st.set_page_config(page_title="TimeFit Agent", page_icon="🏋️")

st.title("🏋️ 시간표 기반 운동 루틴 생성 Agent")
st.write("에브리타임 시간표 이미지를 업로드하면 운동 루틴을 자동 생성합니다.")

# =========================
# 🔐 API KEY 입력
# =========================
api_key = st.text_input(
    "OpenAI API Key 입력",
    type="password",
    placeholder="sk-xxxx..."
)

if not api_key:
    st.warning("API 키를 입력해야 실행됩니다.")
    st.stop()

os.environ["OPENAI_API_KEY"] = api_key

# =========================
# LLM 초기화
# =========================
llm_vision = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)

llm_text = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.7
)

# =========================
# Markdown 후처리 (핵심 패치)
# =========================
def clean_markdown(text: str) -> str:
    """
    LLM 출력 Markdown 깨짐 방지
    """

    if not text:
        return ""

    # 코드블록 제거
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    # 인라인 코드 제거
    text = text.replace("```", "").replace("`", "")

    # 표 앞 공백 제거 (표 인식 실패 방지)
    text = re.sub(r"\n\s+\|", "\n|", text)

    # 불필요 공백 줄이기
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# =========================
# 이미지 인코딩
# =========================
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.read()).decode()


# =========================
# Vision: 시간표 추출
# =========================
def extract_schedule(base64_image):

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": """
에브리타임 시간표 이미지를 분석해서
요일별 일정 시간을 텍스트로 변환하라.

시간 순서:

9,10,11,12,1,2,3,4,5,6,7,8

이는

09~20시 의미 (24시간제 변환).

규칙:

- 텍스트 있으면 일정
- 없으면 공강

출력:

월 09-12 일정
수 공강
"""
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            }
        ]
    )

    response = llm_vision.invoke([message])
    return response.content


# =========================
# 오후 시간 보정
# =========================
def convert_to_24h(schedule_text: str):

    def fix_hour(h):
        h = int(h)
        if 1 <= h <= 8:
            return h + 12
        return h

    pattern = r"(월|화|수|목|금|토|일)\s*(\d{1,2})-(\d{1,2})"

    def repl(m):
        day = m.group(1)
        start = fix_hour(m.group(2))
        end = fix_hour(m.group(3))
        return f"{day} {start:02d}-{end:02d}"

    return re.sub(pattern, repl, schedule_text)


# =========================
# 운동 계획 생성
# =========================
def plan_workout(schedule_text, goal):

    prompt = f"""
사용자 시간표:

{schedule_text}

운동 목표:
{goal}

다음을 Markdown으로 작성:

1. 운동 가능 요일
2. 주간 횟수
3. 분할 루틴

반드시 표 포함.
코드블록 사용 금지.
"""

    res = llm_text.invoke(prompt)
    return res.content


# =========================
# 상세 루틴 생성
# =========================
def generate_routine(plan_text):

    prompt = f"""
다음 계획 기반 상세 루틴 작성:

{plan_text}

Markdown 형식:

- ## 요일 제목
- 운동 표
- 세트 × 횟수
- 휴식시간

코드블록 사용 금지.
"""

    res = llm_text.invoke(prompt)
    return res.content


# =========================
# 사용자 입력
# =========================
goal = st.selectbox(
    "운동 목표 선택",
    ["근비대", "체지방 감량", "체력 향상", "다이어트 + 근육"]
)

uploaded_file = st.file_uploader(
    "시간표 이미지 업로드",
    type=["png", "jpg", "jpeg"]
)

# =========================
# 실행
# =========================
if st.button("운동 루틴 생성"):

    if uploaded_file is None:
        st.warning("이미지를 업로드하세요.")
        st.stop()

    # 시간표 분석
    with st.spinner("시간표 분석 중..."):
        base64_image = encode_image(uploaded_file)
        schedule_text = extract_schedule(base64_image)
        schedule_text = convert_to_24h(schedule_text)

    st.subheader("📅 시간표 분석 결과")
    st.markdown(clean_markdown(schedule_text),
                unsafe_allow_html=True)

    # 운동 계획
    with st.spinner("운동 계획 생성 중..."):
        plan = plan_workout(schedule_text, goal)

    st.subheader("📊 운동 계획")
    st.markdown(clean_markdown(plan),
                unsafe_allow_html=True)

    # 상세 루틴
    with st.spinner("상세 루틴 생성 중..."):
        routine = generate_routine(plan)

    st.subheader("💪 상세 운동 루틴")
    st.markdown(clean_markdown(routine),
                unsafe_allow_html=True)
