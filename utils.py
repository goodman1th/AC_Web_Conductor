import pandas as pd
from io import StringIO
import datetime
import streamlit as st

def log_event(msg):
    ts = datetime.datetime.now().strftime('%H:%M:%S')
    if 'logs' in st.session_state:
        st.session_state.logs.append(f"[{ts}] {msg}")

def read_uploaded_file(uploaded_file):
    """
    업로드된 파일을 읽어서 텍스트 요약본을 반환합니다. (채팅창 Context용)
    """
    try:
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext in ['xlsx', 'xls']:
            df = pd.read_excel(uploaded_file)
            return f"[엑셀 파일 요약]\n- 파일명: {uploaded_file.name}\n- 크기: {df.shape}\n- 컬럼: {list(df.columns)}\n- 데이터 예시:\n{df.head(3).to_string()}"
        elif ext == 'csv':
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='cp949')
            return f"[CSV 파일 요약]\n- 파일명: {uploaded_file.name}\n- 크기: {df.shape}\n- 데이터 예시:\n{df.head(3).to_string()}"
        elif ext in ['txt', 'py', 'json', 'md', 'log']:
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            return f"[텍스트 파일 내용]\n{stringio.read()}"
        else:
            return f"[알림] {uploaded_file.name}은(는) 텍스트로 변환할 수 없는 파일입니다."
    except Exception as e:
        return f"[파일 읽기 오류] {e}"

def get_system_prompt(role):
    """
    각 역할에 맞는 페르소나 프롬프트를 반환합니다.
    """
    prompts = {
        "AC김시율 (Director)": "당신은 AC팀의 총괄 디렉터 'AC김시율'이다. 사용자의 의도를 파악하고, 명확하고 전략적인 지시를 내려라.",
        "PM (Project Manager)": "당신은 전략 기획관(PM)이다. 문제를 해결하기 위한 구체적인 단계와 프롬프트를 설계하라.",
        "Architect (설계자)": "당신은 기술 설계관(Architect)이다. 실행 가능하고 견고한 파이썬 코드를 작성하라.",
        "Executor (수행자)": "당신은 현장 집행관(Executor)이다. 코드를 검증하고 결과를 보고하라.",
        "Scribe (서기)": "당신은 기록 관리관(Scribe)이다. 핵심 정보를 요약하고 파일로 기록하라."
    }
    return prompts.get(role, "당신은 유능한 AI 어시스턴트입니다.")

def analyze_zombie_products(df):
    """
    데이터프레임을 분석하여 '좀비 상품'을 추출합니다.
    분석 과정을 Streamlit 화면에 로그로 출력합니다.
    """
    st.markdown("##### 🕵️ 분석 엔진 로그 (Analysis Log)")
    
    # 1. 컬럼명 전처리 (공백 제거 및 문자열 변환)
    df.columns = [str(c).strip() for c in df.columns]
    cols = df.columns.tolist()

    # 2. 헤더 이상 감지
    if cols[0].startswith('20') and cols[0].isdigit():
        st.warning(f"⚠️ 경고: 첫 번째 컬럼이 날짜({cols[0]})로 보입니다. 제목줄이 누락되었거나 밀렸을 수 있습니다.")

    # 3. 키워드 기반 컬럼 매핑
    def find_col(keywords):
        for col in cols:
            for kw in keywords:
                if kw.lower() in col.lower():
                    return col
        return None

    cost_col = find_col(['광고비', '비용', 'cost', 'salesAmt', '지출'])
    sales_col = find_col(['전환매출', '매출', 'sales', 'convAmt', '수익'])
    imp_col = find_col(['노출', 'imp', 'view'])
    clk_col = find_col(['클릭', 'clk', 'click'])
    
    # 4. 매핑 결과 보고
    if cost_col and sales_col and imp_col and clk_col:
        st.success(f"✅ 컬럼 매핑 성공:\n- 비용: {cost_col}\n- 매출: {sales_col}\n- 노출: {imp_col}\n- 클릭: {clk_col}")
    else:
        st.error(f"❌ 필수 컬럼 매핑 실패:\n- 비용: {cost_col}\n- 매출: {sales_col}\n- 노출: {imp_col}\n- 클릭: {clk_col}")
        raise ValueError("분석에 필요한 필수 컬럼(비용, 매출, 노출, 클릭)을 찾을 수 없습니다. 엑셀 파일의 제목줄을 확인해주세요.")

    # 5. 데이터 타입 변환 (숫자화)
    for c in [cost_col, sales_col, imp_col, clk_col]:
        df[c] = df[c].astype(str).str.replace(',', '').str.replace(' ', '')
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 6. 좀비 필터링 로직
    # A그룹: 돈만 쓰는 놈 (비용 >= 5000 AND 매출 == 0)
    # B그룹: 관심만 끄는 놈 (노출 >= 100 AND 클릭 == 0)
    zombie_condition = ((df[cost_col] >= 5000) & (df[sales_col] == 0)) | \
                       ((df[imp_col] >= 100) & (df[clk_col] == 0))

    zombies = df[zombie_condition].copy()
    
    return zombies

def generate_kill_list_filename():
    """
    현재 날짜 기반으로 살생부 파일명을 생성합니다.
    """
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"