import pandas as pd
from io import StringIO
import datetime
import streamlit as st

def log_event(msg):
    ts = datetime.datetime.now().strftime('%H:%M:%S')
    if 'logs' in st.session_state: st.session_state.logs.append(f"[{ts}] {msg}")

def read_uploaded_file(uploaded_file):
    try:
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext in ['xlsx', 'xls']: df = pd.read_excel(uploaded_file)
        elif ext == 'csv':
            try: df = pd.read_csv(uploaded_file, encoding='utf-8')
            except: uploaded_file.seek(0); df = pd.read_csv(uploaded_file, encoding='cp949')
        else: return f"텍스트 변환 불가: {uploaded_file.name}"
        return f"[데이터 요약]\n크기: {df.shape}\n상위 3행:\n{df.head(3).to_string()}"
    except Exception as e: return f"[읽기 오류] {e}"

def get_system_prompt(role):
    # 역할별 진실한 페르소나 정의
    return "당신은 AC팀의 일원이다. 주어진 역할에 충실하고 거짓 없이 수행하라."

def analyze_zombie_products(df):
    st.markdown("##### 🕵️ 데이터 분석 로그 (Truth Log)")
    df.columns = [str(c).strip() for c in df.columns]
    cols = df.columns.tolist()

    # 헤더 감지 및 보고
    if cols[0].startswith('20') and cols[0].isdigit():
        st.warning(f"⚠️ 제목줄이 날짜({cols[0]})로 보입니다. 데이터가 밀렸을 수 있습니다.")

    # 컬럼 찾기 (유연한 검색)
    def find(kws):
        for c in cols:
            for k in kws:
                if k.lower() in c.lower(): return c
        return None

    cost = find(['광고비', '비용', 'cost', 'salesAmt', '지출'])
    sales = find(['전환매출', '매출', 'sales', 'convAmt', '수익'])
    imp = find(['노출', 'imp', 'view'])
    clk = find(['클릭', 'clk', 'click'])
    
    # 매핑 결과 이실직고
    if cost and sales and imp and clk:
        st.success(f"✅ 매핑 완료: 비용[{cost}], 매출[{sales}], 노출[{imp}], 클릭[{clk}]")
    else:
        st.error(f"❌ 매핑 실패: 비용[{cost}], 매출[{sales}], 노출[{imp}], 클릭[{clk}]")
        raise ValueError("필수 컬럼을 찾지 못했습니다. 위 로그를 확인하세요.")

    # 정제 및 필터링
    for c in [cost, sales, imp, clk]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    cond = ((df[cost] >= 5000) & (df[sales] == 0)) | ((df[imp] >= 100) & (df[clk] == 0))
    return df[cond].copy()

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"