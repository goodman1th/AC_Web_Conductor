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
        else: return f"변환 불가: {uploaded_file.name}"
        return f"[데이터 요약]\n크기: {df.shape}\n상위 3행:\n{df.head(3).to_string()}"
    except Exception as e: return f"[읽기 오류] {e}"

def get_system_prompt(role):
    return "당신은 AC팀의 일원이다. 주어진 역할에 충실하라."

def analyze_zombie_products(df):
    """
    [v5.0 Final] 적응형 하이브리드 분석기
    1. 파일에 이미 헤더가 있는지 확인합니다. (키워드 검색)
    2. 있다면 -> 그 헤더를 존중하여 사용합니다.
    3. 없다면 -> 네이버 표준 스키마를 강제 적용합니다.
    """
    
    # 1. 컬럼명 전처리 (공백 제거)
    df.columns = [str(c).strip() for c in df.columns]
    current_cols = df.columns.tolist()

    # ---------------------------------------------------------
    # [Step A] 기존 헤더 존재 여부 판단 (Header Sniffing)
    # ---------------------------------------------------------
    # 이 단어들이 컬럼명에 하나라도 포함되어 있다면, 이미 헤더가 있는 파일임.
    header_keywords = ['비용', 'Cost', '광고비', '매출', 'Sales', '노출', 'Imp', '클릭', 'Click', '소재', '키워드']
    
    has_header = any(k.lower() in str(c).lower() for c in current_cols for k in header_keywords)
    
    # 날짜(숫자)로 시작하는지 체크 (헤더가 아니라 데이터일 확률 높음)
    first_val = str(current_cols[0])
    is_data_row = first_val.startswith('20') and first_val.isdigit()

    # ---------------------------------------------------------
    # [Step B] 상황별 대응
    # ---------------------------------------------------------
    if has_header and not is_data_row:
        # [Case 1] 제목이 있는 정상 파일
        st.info("💡 파일에 포함된 '기존 제목'을 그대로 사용합니다.")
        
    else:
        # [Case 2] 제목이 없는 API 원본 파일 (숫자로 시작하거나 키워드 없음)
        st.warning(f"🚨 제목줄이 감지되지 않았습니다. (첫 행: {first_val})\n👉 네이버 표준 양식을 적용합니다.")
        
        # 첫 줄을 데이터로 내리기
        new_row = pd.DataFrame([current_cols], columns=current_cols)
        df = pd.concat([new_row, df], ignore_index=True)
        
        # 표준 스키마 적용 (가장 흔한 14열/12열 대응)
        col_count = len(df.columns)
        
        schema_14 = ['날짜', '고객ID', '캠페인ID', '광고그룹ID', '키워드ID', '키워드명', '매체', '지역', '순위', '노출수', '클릭수', '광고비(원)', '전환수', '전환매출액(원)']
        schema_12 = ['날짜', '캠페인ID', '광고그룹ID', '키워드ID', '키워드명', '매체', '노출수', '클릭수', '클릭률', '평균클릭비용', '광고비(원)', '전환매출액(원)']

        if col_count == 14:
            df.columns = schema_14
        elif col_count == 12:
            df.columns = schema_12
        else:
            # 열 개수가 애매하면 '스마트 역순 매핑' (성과지표는 무조건 뒤에 있음)
            st.info("⚠️ 열 개수가 표준과 달라, 핵심 지표를 뒤에서부터 매칭합니다.")
            cols = [f"Col_{i}" for i in range(col_count)]
            cols[-1] = '전환매출액(원)'
            cols[-3] = '광고비(원)'
            cols[-4] = '클릭수'
            cols[-5] = '노출수'
            cols[0] = '날짜'
            df.columns = cols
            
    # 컬럼 목록 갱신
    current_cols = df.columns.tolist()

    # ---------------------------------------------------------
    # [Step C] 유연한 컬럼 찾기 (Fuzzy Logic)
    # ---------------------------------------------------------
    def find_col(keywords):
        for col in current_cols:
            for kw in keywords:
                if kw.lower() in col.lower(): return col
        return None

    cost = find_col(['광고비', '비용', 'cost', 'salesAmt', '지출'])
    sales = find_col(['전환매출', '매출', 'sales', 'convAmt', '수익'])
    imp = find_col(['노출', 'imp', 'view'])
    clk = find_col(['클릭', 'clk', 'click'])

    # ---------------------------------------------------------
    # [Step D] 사용자에게 보고 (Visual Check)
    # ---------------------------------------------------------
    with st.expander("🔎 데이터 매핑 결과 확인 (여기를 클릭하세요)", expanded=True):
        if cost and sales and imp and clk:
            st.success(f"✅ 매핑 성공!\n- 비용: {cost}\n- 매출: {sales}\n- 노출: {imp}\n- 클릭: {clk}")
            st.dataframe(df.head(3)) # 데이터와 제목이 맞는지 눈으로 확인
        else:
            st.error(f"❌ 매핑 실패 (찾지 못한 항목이 있습니다)\n- 비용:{cost}, 매출:{sales}, 노출:{imp}, 클릭:{clk}")
            st.stop() # 더 이상 진행하지 않고 멈춤

    # ---------------------------------------------------------
    # [Step E] 데이터 정제 및 필터링
    # ---------------------------------------------------------
    for c in [cost, sales, imp, clk]:
        df[c] = df[c].astype(str).str.replace(',', '').str.replace(' ', '')
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 좀비 조건: (돈 썼는데 매출 0) OR (노출됐는데 클릭 0)
    cond = ((df[cost] >= 5000) & (df[sales] == 0)) | \
           ((df[imp] >= 100) & (df[clk] == 0))
           
    zombies = df[cond].copy()
    
    return zombies

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"