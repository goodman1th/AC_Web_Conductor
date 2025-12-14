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
            # CSV는 인코딩 문제가 많으므로 utf-8, cp949 순차 시도
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
            
        return f"[데이터 요약]\n크기: {df.shape}\n컬럼명: {list(df.columns)}\n상위 3행:\n{df.head(3).to_string()}"
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
    데이터프레임을 분석하여 좀비 상품을 찾습니다.
    (헤더가 없거나 이름이 달라도 유연하게 대처)
    """
    # 1. 컬럼명 정제 (공백 제거)
    df.columns = [str(c).strip() for c in df.columns]
    cols = df.columns.tolist()

    # 2. [헤더 누락 감지] 첫 번째 컬럼 이름이 날짜 숫자(예: 20251214)인 경우
    first_col = str(cols[0])
    if first_col.startswith('20') and len(first_col) == 8 and first_col.isdigit():
        st.warning(f"🚨 파일에 제목줄이 없어 보입니다. (첫 행: {first_col})\n강제로 표준 헤더를 적용합니다.")
        
        # 현재 헤더로 인식된 첫 줄을 데이터로 내림
        new_row = pd.DataFrame([cols], columns=cols)
        df = pd.concat([new_row, df], ignore_index=True)
        
        # 표준 네이버 리포트 순서대로 컬럼명 강제 할당 (가장 흔한 14열 기준)
        # 만약 열 개수가 다르면, 뒤에서부터 중요 데이터를 매칭함
        if len(cols) >= 10:
            # 임시 이름 부여
            df.columns = [f"Col_{i}" for i in range(len(cols))]
            # 뒤에서부터 매칭 (보통 끝부분에 지표가 있음)
            rename_map = {
                df.columns[-1]: '전환매출액(원)', # 맨 뒤
                df.columns[-3]: '광고비(원)',     # 뒤에서 3번째
                df.columns[-4]: '클릭수',         # 뒤에서 4번째
                df.columns[-5]: '노출수',         # 뒤에서 5번째
                df.columns[0]: '날짜'
            }
            df.rename(columns=rename_map, inplace=True)
        else:
            raise ValueError(f"데이터 열 개수가 너무 적습니다. ({len(cols)}개). 올바른 리포트인지 확인해주세요.")
            
        cols = df.columns.tolist() # 갱신

    # 3. 컬럼 찾기 (키워드 검색)
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

    # 4. 필수 컬럼 검사 및 오류 보고
    if not all([cost, sales, imp, clk]):
        found_status = f"비용[{cost}] 매출[{sales}] 노출[{imp}] 클릭[{clk}]"
        raise ValueError(
            f"분석에 필요한 컬럼을 찾지 못했습니다.\n"
            f"- 현재 인식된 컬럼 목록: {cols}\n"
            f"- 매칭 현황: {found_status}\n"
            f"- 해결책: 파일에 [광고비, 매출, 노출수, 클릭수] 제목이 있는지 확인하세요."
        )

    # 5. 데이터 타입 변환 (숫자로)
    for c in [cost, sales, imp, clk]:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 6. 필터링 (좀비 색출)
    # 조건: 돈(5000원 이상) 썼는데 매출 0 OR 노출(100회 이상) 됐는데 클릭 0
    cond_zombie = ((df[cost] >= 5000) & (df[sales] == 0)) | \
                  ((df[imp] >= 100) & (df[clk] == 0))

    zombies = df[cond_zombie].copy()
    
    # 결과 컬럼 정리 (중요한 것만)
    display_cols = [c for c in cols if c in [cost, sales, imp, clk] or 'ID' in c or '명' in c]
    if not display_cols: display_cols = cols
    
    return zombies[display_cols]

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"