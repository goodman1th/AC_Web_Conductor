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
    cols = df.columns
    
    # [안전장치] 헤더가 데이터(날짜 등)로 인식된 경우 감지
    first_col = str(cols[0])
    if first_col.startswith('202') and len(first_col) == 8 and first_col.isdigit():
        raise ValueError(
            "🚨 파일에 '제목줄(Header)'이 없습니다.\n"
            "현재 첫 번째 줄이 날짜 데이터로 인식됩니다.\n"
            "파일 맨 윗줄에 [날짜, 노출수, 클릭수, 광고비, 전환매출액] 같은 제목을 추가하거나,\n"
            "'실행실' 탭에서 리포트를 새로 추출해서 사용해 주세요."
        )

    # 1. 비용 컬럼 찾기 (우선순위: 광고비(원) -> salesAmt)
    cost_candidates = ['광고비(원)', '총비용(VAT포함)', '총비용', '비용', 'salesAmt']
    cost = next((c for c in cost_candidates if c in cols), None)
    
    # 2. 매출 컬럼 찾기
    sales_candidates = ['전환매출액(원)', '총전환매출', '전환매출', '매출', 'convAmt']
    sales = next((c for c in sales_candidates if c in cols), None)
    
    # 3. 노출/클릭 컬럼 찾기
    imp_candidates = ['노출수', 'impCnt']
    imp = next((c for c in imp_candidates if c in cols), None)
    
    clk_candidates = ['클릭수', 'clkCnt']
    clk = next((c for c in clk_candidates if c in cols), None)

    # 필수 컬럼 검사
    if not all([cost, sales, imp, clk]):
        missing = []
        if not cost: missing.append(f"비용 (예: {cost_candidates})")
        if not sales: missing.append(f"매출 (예: {sales_candidates})")
        if not imp: missing.append("노출수")
        if not clk: missing.append("클릭수")
        
        raise ValueError(
            f"필수 데이터 컬럼을 찾을 수 없습니다.\n"
            f"- 누락된 항목: {', '.join(missing)}\n"
            f"- 현재 파일의 컬럼: {list(cols)}"
        )

    # 필터링 로직
    cond_a = (df[cost] >= 5000) & (df[sales] == 0)
    cond_b = (df[imp] >= 100) & (df[clk] == 0)

    zombies = df[cond_a | cond_b].copy()
    
    return zombies

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"