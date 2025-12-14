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
        elif ext == 'csv':
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='cp949')
        elif ext in ['txt', 'py', 'json', 'md', 'log']:
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            return f"[파일 내용]\n{stringio.read()}"
        else:
            return f"[알림] {uploaded_file.name} 텍스트 변환 불가"
            
        return f"[데이터 요약]\n크기: {df.shape}\n상위 5행:\n{df.head(5).to_string()}"
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
    [v2.9 Update] 헤더 채점 방식 도입
    데이터(숫자)를 헤더로 착각하는 오류를 방지합니다.
    """
    
    # -----------------------------------------------------------
    # [Step 1] 헤더 수색 작전 (Scoring System)
    # -----------------------------------------------------------
    # 이 단어들이 많이 포함된 줄일수록 '진짜 제목줄'일 확률이 높음
    keywords = ['광고비', '비용', 'salesAmt', '노출', 'imp', '클릭', 'clk', '전환', '매출', 'conv']
    
    best_header_idx = -1
    max_score = 0
    
    # 상위 15줄을 검사
    for i, row in df.head(15).iterrows():
        # 해당 행을 문자열로 변환하여 키워드 몇 개나 포함하는지 채점
        row_str = " ".join([str(x).lower() for x in row.values])
        score = sum(1 for k in keywords if k in row_str)
        
        if score > max_score:
            max_score = score
            best_header_idx = i
            
    # -----------------------------------------------------------
    # [Step 2] 헤더 적용 또는 강제 할당
    # -----------------------------------------------------------
    if max_score >= 2: # 키워드가 2개 이상 발견된 줄이 있다면 그것을 헤더로 채택
        st.info(f"💡 {best_header_idx+1}번째 줄을 '제목줄'로 인식했습니다. (일치 점수: {max_score})")
        df.columns = df.iloc[best_header_idx] # 그 줄을 컬럼명으로
        df = df[best_header_idx+1:].reset_index(drop=True) # 그 윗줄 삭제
    else:
        # 키워드 발견 실패 -> 제목 없는 파일로 간주 -> 강제 할당
        st.warning("⚠️ 명확한 제목줄을 찾을 수 없습니다. 표준 네이버 양식으로 강제 설정합니다.")
        
        # 열 개수에 따라 표준 이름 부여
        # 네이버 기본 14열 기준
        standard_cols = [
            '날짜', '고객ID', '캠페인ID', '광고그룹ID', '키워드ID', '키워드명', 
            '기타1', '기타2', '기타3', '노출수', '클릭수', '광고비(원)', '전환수', '전환매출액(원)'
        ]
        
        current_col_count = len(df.columns)
        if current_col_count >= 10:
            # 개수가 많으면 뒤에서부터 매핑 (보통 뒤에 숫자가 있음)
            new_cols = [f"Col_{i}" for i in range(current_col_count)]
            new_cols[-1] = '전환매출액(원)'
            new_cols[-3] = '광고비(원)'
            new_cols[-4] = '클릭수'
            new_cols[-5] = '노출수'
            new_cols[0] = '날짜'
            df.columns = new_cols
        else:
            raise ValueError(f"데이터 열 개수가 너무 적습니다 ({current_col_count}개). 리포트 파일을 확인해주세요.")

    # -----------------------------------------------------------
    # [Step 3] 컬럼명 정제 (문자열로 변환 및 공백 제거)
    # -----------------------------------------------------------
    # 여기가 핵심: 컬럼명이 숫자로 되어있으면 에러나므로 전부 문자로 바꿈
    df.columns = [str(c).strip() for c in df.columns]
    cols = df.columns.tolist()

    # -----------------------------------------------------------
    # [Step 4] 타겟 컬럼 찾기 (유연한 매칭)
    # -----------------------------------------------------------
    def find_col(kws):
        for col in cols:
            for kw in kws:
                if kw.lower() in col.lower(): return col
        return None

    cost = find_col(['광고비', '총비용', 'salesAmt', '비용', 'Cost'])
    sales = find_col(['전환매출', '매출', 'convAmt', 'Sales'])
    imp = find_col(['노출', 'impCnt', 'Imp'])
    clk = find_col(['클릭', 'clkCnt', 'Click'])

    if not all([cost, sales, imp, clk]):
        raise ValueError(
            f"분석에 필요한 컬럼을 확정하지 못했습니다.\n"
            f"- 찾은 항목: 비용[{cost}] 매출[{sales}] 노출[{imp}] 클릭[{clk}]\n"
            f"- 현재 컬럼 목록: {cols}"
        )

    # -----------------------------------------------------------
    # [Step 5] 데이터 타입 강제 변환 (숫자화)
    # -----------------------------------------------------------
    for c in [cost, sales, imp, clk]:
        # 콤마, 공백 제거 후 숫자로 변환 (에러나면 0으로 처리)
        df[c] = df[c].astype(str).str.replace(',', '').str.replace(' ', '')
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # -----------------------------------------------------------
    # [Step 6] 좀비 필터링
    # -----------------------------------------------------------
    cond_a = (df[cost] >= 5000) & (df[sales] == 0)
    cond_b = (df[imp] >= 100) & (df[clk] == 0)

    zombies = df[cond_a | cond_b].copy()
    
    # 출력용 컬럼 정리
    display_cols = [c for c in cols if c in [cost, sales, imp, clk] or 'ID' in c or '명' in c or '날짜' in c]
    if not display_cols: display_cols = cols
    
    return zombies[display_cols]

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"