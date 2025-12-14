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
            
        return f"[데이터 요약]\n크기: {df.shape}\n상위 3행:\n{df.head(3).to_string()}"
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
    [v3.0] 매핑 결과 중계 기능 탑재
    """
    st.markdown("##### 🕵️ 데이터 분석 로그")
    
    # 1. 컬럼명 문자열 변환 및 공백 제거
    df.columns = [str(c).strip() for c in df.columns]
    cols = df.columns.tolist()
    
    # 2. 헤더 감지 로직 (숫자로 시작하면 경고)
    if cols[0].startswith('20') and cols[0].isdigit():
        st.warning(f"⚠️ 제목줄이 날짜({cols[0]})로 인식됩니다. 수정하신 파일이 맞나요?")
        # (필요 시 v2.9의 헤더 강제 할당 로직을 여기에 추가 가능)

    # 3. 컬럼 찾기 함수 (대소문자 무시)
    def find_col(keywords):
        for col in cols:
            for kw in keywords:
                if kw.lower() in col.lower(): return col
        return None

    # 키워드 확장 (파트너님이 수정했을 법한 이름들 포함)
    cost = find_col(['광고비', '비용', 'cost', 'salesAmt', '지출'])
    sales = find_col(['전환매출', '매출', 'sales', 'convAmt', '수익'])
    imp = find_col(['노출', 'imp', 'view'])
    clk = find_col(['클릭', 'clk', 'click'])
    
    # 4. [핵심] 매핑 결과 리포트 (화면에 출력)
    if cost: st.success(f"✅ 비용 열 확인: **{cost}**")
    else: st.error("❌ 비용 열을 못 찾았습니다. (예: 광고비, Cost)")
    
    if sales: st.success(f"✅ 매출 열 확인: **{sales}**")
    else: st.error("❌ 매출 열을 못 찾았습니다. (예: 전환매출, Sales)")
    
    if imp and clk: st.success(f"✅ 노출/클릭 확인: **{imp} / {clk}**")
    else: st.error(f"❌ 노출/클릭 확인 불가: {imp} / {clk}")

    # 5. 필수 컬럼 부재 시 중단
    if not all([cost, sales, imp, clk]):
        raise ValueError("필수 컬럼 매핑에 실패했습니다. 위의 ❌ 표시를 확인해주세요.")

    # 6. 데이터 정제 (숫자만 남기기)
    for c in [cost, sales, imp, clk]:
        df[c] = df[c].astype(str).str.replace(',', '').str.replace(' ', '')
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 7. 좀비 필터링
    cond_a = (df[cost] >= 5000) & (df[sales] == 0)
    cond_b = (df[imp] >= 100) & (df[clk] == 0)
    
    zombies = df[cond_a | cond_b].copy()
    
    # 디스플레이용 컬럼 선택
    display_cols = [c for c in cols if c in [cost, sales, imp, clk] or 'ID' in c or '명' in c or '날짜' in c]
    
    return zombies[display_cols if display_cols else cols]

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"