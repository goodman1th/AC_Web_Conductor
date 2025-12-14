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
    데이터프레임의 '진짜 헤더'를 찾아서 좀비 상품을 분석합니다.
    (밀림 현상 방지 로직 탑재)
    """
    
    # -----------------------------------------------------------
    # [Step 1] 진짜 제목줄(Header) 위치 찾기 (Header Sniffer)
    # -----------------------------------------------------------
    # 찾을 키워드 목록
    target_keywords = ['광고비', '비용', 'salesAmt', '노출수', 'impCnt', '클릭수', 'clkCnt']
    
    header_idx = -1
    
    # 1-1. 현재 컬럼명에 키워드가 있는지 확인 (이미 정상인 경우)
    current_cols = [str(c) for c in df.columns]
    if any(k in str(c) for c in current_cols for k in target_keywords):
        header_idx = -1 # 현재 상태가 정상
    else:
        # 1-2. 상위 10행을 뒤져서 키워드가 포함된 행 찾기
        for i, row in df.head(10).iterrows():
            row_str = " ".join([str(x) for x in row.values])
            # 해당 행에 '광고비'나 '노출수' 같은 단어가 포함되어 있다면?
            if any(k in row_str for k in target_keywords):
                header_idx = i
                break
    
    # 1-3. 헤더 교체 실행
    if header_idx != -1:
        st.info(f"💡 {header_idx+1}번째 줄에서 '진짜 제목'을 찾았습니다. 데이터를 정렬합니다.")
        # 해당 행을 컬럼명으로 승격
        df.columns = df.iloc[header_idx]
        # 그 윗줄 데이터와 헤더행 자체를 삭제
        df = df[header_idx+1:].reset_index(drop=True)

    # -----------------------------------------------------------
    # [Step 2] 컬럼 매핑 (유연한 검색)
    # -----------------------------------------------------------
    cols = [str(c).strip() for c in df.columns]
    df.columns = cols # 공백 제거된 컬럼명 적용

    def find_col(keywords):
        for col in cols:
            for kw in keywords:
                if kw.lower() in col.lower():
                    return col
        return None

    cost = find_col(['광고비', '총비용', 'salesAmt', '비용', 'Cost'])
    sales = find_col(['전환매출', '매출', 'convAmt', 'Sales', 'Rev'])
    imp = find_col(['노출', 'impCnt', 'Imp'])
    clk = find_col(['클릭', 'clkCnt', 'Click'])

    # -----------------------------------------------------------
    # [Step 3] 필수 컬럼 검사
    # -----------------------------------------------------------
    if not all([cost, sales, imp, clk]):
        # 최후의 수단: 강제 할당 (헤더가 아예 없는 경우)
        if len(cols) >= 10:
            st.warning("⚠️ 제목줄을 찾지 못해 '표준 네이버 양식'으로 강제 매핑합니다.")
            # 뒤에서부터 매칭
            df.columns.values[-1] = '전환매출액(원)'
            df.columns.values[-3] = '광고비(원)'
            df.columns.values[-4] = '클릭수'
            df.columns.values[-5] = '노출수'
            
            cost, sales, imp, clk = '광고비(원)', '전환매출액(원)', '노출수', '클릭수'
        else:
            raise ValueError(
                f"데이터 구조 분석 실패.\n"
                f"- 현재 인식된 컬럼: {cols}\n"
                f"- 해결책: 엑셀 파일을 열어서 맨 윗줄에 [광고비, 매출, 노출수, 클릭수]가 있는지 확인하세요."
            )

    # -----------------------------------------------------------
    # [Step 4] 데이터 정제 및 필터링
    # -----------------------------------------------------------
    # 숫자 변환 (콤마, 문자 제거)
    for c in [cost, sales, imp, clk]:
        df[c] = df[c].astype(str).str.replace(',', '').str.replace(' ', '')
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 좀비 조건
    cond_a = (df[cost] >= 5000) & (df[sales] == 0)
    cond_b = (df[imp] >= 100) & (df[clk] == 0)

    zombies = df[cond_a | cond_b].copy()
    
    # 보기 좋게 컬럼 선택
    display_cols = [c for c in cols if c in [cost, sales, imp, clk] or 'ID' in c or '명' in c or '날짜' in c]
    if not display_cols: display_cols = cols
    
    return zombies[display_cols]

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"