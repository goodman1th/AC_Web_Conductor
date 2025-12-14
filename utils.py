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
    네이버 리포트 데이터프레임을 분석합니다.
    (헤더가 없는 경우 자동 복구 기능 추가)
    """
    cols = df.columns
    
    # 1. [자동 복구] 헤더가 날짜 데이터로 인식된 경우 (제목줄 누락 감지)
    first_col = str(cols[0])
    if first_col.startswith('202') and len(first_col) == 8 and first_col.isdigit():
        st.warning("🚨 파일에 제목줄이 없습니다. '표준 네이버 양식'으로 간주하고 자동 복구합니다.")
        
        # 현재 df는 첫 줄이 헤더로 잘못 들어가 있으므로, 데이터를 포함하여 다시 정리
        # (주의: Streamlit에서는 이미 읽은 파일을 다시 읽으려면 seek(0) 필요하지만, 
        # 여기서는 df를 받으므로 컬럼을 데이터로 내리는 방식 사용)
        
        # 1. 현재 컬럼명을 데이터의 첫 행으로 추가
        new_row = pd.DataFrame([df.columns], columns=df.columns)
        df = pd.concat([new_row, df], ignore_index=True)
        
        # 2. 표준 컬럼명 강제 할당 (네이버 API 표준 순서 추정)
        # 보통: 날짜, ID, 캠페인, 그룹, 키워드ID, 키워드명, 노출, 클릭, 비용, 매출...
        # 파트너님 데이터(14개)에 맞춘 추정 매핑
        standard_cols = [
            '날짜', '고객ID', '캠페인ID', '광고그룹ID', '키워드ID', '키워드명', 
            '기타1', '기타2', '기타3', '노출수', '클릭수', '광고비(원)', '전환수', '전환매출액(원)'
        ]
        
        # 컬럼 수가 맞으면 매핑, 안 맞으면 최대한 맞춤
        if len(df.columns) == len(standard_cols):
            df.columns = standard_cols
        else:
            # 개수가 다르면 뒤에서부터 매칭 (비용, 매출은 보통 뒤에 있음)
            # 임시 컬럼명 생성
            df.columns = [f"Col_{i}" for i in range(len(df.columns))]
            # 주요 컬럼 추정 (뒤에서부터)
            rename_map = {
                df.columns[-1]: '전환매출액(원)', # 맨 뒤
                df.columns[-3]: '광고비(원)',     # 뒤에서 3번째
                df.columns[-4]: '클릭수',         # 뒤에서 4번째
                df.columns[-5]: '노출수',         # 뒤에서 5번째
                df.columns[0]: '날짜'
            }
            df.rename(columns=rename_map, inplace=True)
            
        cols = df.columns # 갱신

    # 2. 비용 컬럼 찾기
    cost_candidates = ['광고비(원)', '총비용', '비용', 'salesAmt', 'Col_11'] # Col_11은 14개 기준 추정치
    cost = next((c for c in cost_candidates if c in cols), None)
    
    # 3. 매출 컬럼 찾기
    sales_candidates = ['전환매출액(원)', '전환매출', '매출', 'convAmt', 'Col_13']
    sales = next((c for c in sales_candidates if c in cols), None)
    
    # 4. 노출/클릭 컬럼 찾기
    imp = next((c for c in ['노출수', 'impCnt', 'Col_9'] if c in cols), None)
    clk = next((c for c in ['클릭수', 'clkCnt', 'Col_10'] if c in cols), None)

    # 필수 컬럼 검사
    if not all([cost, sales, imp, clk]):
        raise ValueError(
            f"데이터 구조를 파악할 수 없습니다.\n"
            f"- 찾은 항목: 비용({cost}), 매출({sales}), 노출({imp}), 클릭({clk})\n"
            f"- 해결책: [Tab 2: 실행실]에서 리포트를 새로 추출하여 사용하십시오."
        )

    # 데이터 타입 변환 (문자열이 섞여있을 수 있으므로)
    for col in [cost, sales, imp, clk]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 필터링 로직
    cond_a = (df[cost] >= 5000) & (df[sales] == 0)
    cond_b = (df[imp] >= 100) & (df[clk] == 0)

    zombies = df[cond_a | cond_b].copy()
    return zombies

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"