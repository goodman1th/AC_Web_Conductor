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
    (컬럼명이 달라도 유연하게 찾도록 개선됨)
    """
    cols = df.columns
    
    # 1. 비용 컬럼 찾기 (우선순위: 광고비(원) -> 총비용 -> 비용 -> salesAmt)
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
        if not cost: missing.append(f"비용(예: {cost_candidates})")
        if not sales: missing.append(f"매출(예: {sales_candidates})")
        if not imp: missing.append("노출수")
        if not clk: missing.append("클릭수")
        
        # 상세 에러 메시지 반환
        raise ValueError(
            f"필수 데이터 컬럼을 찾을 수 없습니다.\n"
            f"- 누락된 항목: {', '.join(missing)}\n"
            f"- 현재 파일의 컬럼 목록: {list(cols)}"
        )

    # 필터링 로직
    # 조건 A: 돈은 많이 썼는데(5000원 이상) 매출이 0원
    cond_a = (df[cost] >= 5000) & (df[sales] == 0)
    # 조건 B: 노출은 많이 됐는데(100회 이상) 클릭이 0회 (관심 밖)
    cond_b = (df[imp] >= 100) & (df[clk] == 0)

    zombies = df[cond_a | cond_b].copy()
    
    # 결과 보기 좋게 정리 (선택 사항)
    display_cols = [c for c in cols if c in [cost, sales, imp, clk, '캠페인ID', '키워드ID', '광고그룹ID', '키워드명']]
    if not display_cols: display_cols = cols # 매칭 안되면 전체 출력
    
    return zombies[display_cols] if len(display_cols) > 0 else zombies

def generate_kill_list_filename():
    """
    살생부 파일 이름을 생성합니다.
    """
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"