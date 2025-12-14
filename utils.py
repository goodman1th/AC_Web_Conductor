import pandas as pd
from io import StringIO
import datetime
import streamlit as st

def log_event(msg):
    ts = datetime.datetime.now().strftime('%H:%M:%S')
    if 'logs' in st.session_state:
        st.session_state.logs.append(f"[{ts}] {msg}")

def read_uploaded_file(uploaded_file):
    try:
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext in ['xlsx', 'xls']:
            df = pd.read_excel(uploaded_file)
            return f"[엑셀 요약]\n크기: {df.shape}\n컬럼: {list(df.columns)}\n상위 5행:\n{df.head().to_string()}"
        elif ext == 'csv':
            df = pd.read_csv(uploaded_file)
            return f"[CSV 요약]\n{df.head().to_string()}"
        elif ext in ['txt', 'py', 'json', 'md', 'log']:
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            return f"[파일 내용]\n{stringio.read()}"
        else:
            return f"[알림] {uploaded_file.name} 텍스트 변환 불가"
    except Exception as e:
        return f"[파일 읽기 오류] {e}"

def get_system_prompt(role):
    prompts = {
        "AC김시율 (Director)": "당신은 총괄 디렉터다. 핵심만 명확하게 지시하라.",
        "PM (Project Manager)": "당신은 PM이다. 업무를 구조화하라.",
        "Architect (설계자)": "당신은 설계자다. 실행 가능한 파이썬 코드를 작성하라.",
        "Executor (수행자)": "당신은 수행자다. 결과만 보고하라.",
        "Scribe (서기)": "당신은 서기다. 팩트만 기록하라."
    }
    return prompts.get(role, "")

def analyze_zombie_products(df):
    """
    네이버 리포트 데이터프레임을 분석하여 '돈만 먹는 상품'을 식별합니다.
    """
    # 컬럼 매핑 (한글/영어 호환)
    cols = df.columns
    cost = '광고비(원)' if '광고비(원)' in cols else 'salesAmt'
    sales = '전환매출액(원)' if '전환매출액(원)' in cols else 'convAmt'
    imp = '노출수' if '노출수' in cols else 'impCnt'
    clk = '클릭수' if '클릭수' in cols else 'clkCnt'

    # 필터링 조건
    cond_a = (df[cost] >= 5000) & (df[sales] == 0)
    cond_b = (df[imp] >= 100) & (df[clk] == 0)

    zombies = df[cond_a | cond_b].copy()
    return zombies

def generate_kill_list_filename():
    """
    살생부 파일 이름을 생성합니다.
    """
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"