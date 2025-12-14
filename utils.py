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
    return "당신은 AC팀의 일원이다. 맡은 임무를 정확히 수행하라."

def analyze_zombie_products(df):
    """
    [v4.2 Final] 차분한 UI 버전
    과도한 텍스트 출력을 줄이고, 데이터 자체로 증명합니다.
    """
    
    # 1. 데이터 정리 (헤더가 없는 API 원본 대응)
    df.columns = [str(c).strip() for c in df.columns]
    first_val = df.columns[0]
    
    if first_val.startswith('20') and first_val.isdigit():
        new_row = pd.DataFrame([df.columns], columns=df.columns)
        df = pd.concat([new_row, df], ignore_index=True)
        # 조용히 처리 (로그 제거)

    # 2. 공식 스키마 정의
    col_count = len(df.columns)
    
    schema_14 = [
        '날짜', '고객ID', '캠페인ID', '광고그룹ID', '키워드ID', '키워드명', 
        '매체', '지역', '순위', '노출수', '클릭수', '광고비(원)', '전환수', '전환매출액(원)'
    ]
    
    schema_12 = [
        '날짜', '캠페인ID', '광고그룹ID', '키워드ID', '키워드명', 
        '매체', '노출수', '클릭수', '클릭률', '평균클릭비용', '광고비(원)', '전환매출액(원)'
    ]

    # 스키마 매핑
    msg = ""
    if col_count == 14:
        df.columns = schema_14
        msg = "✅ 표준 14열 스키마 적용"
    elif col_count == 12:
        df.columns = schema_12
        msg = "✅ 표준 12열 스키마 적용"
    else:
        cols = [f"Col_{i}" for i in range(col_count)]
        cols[-1] = '전환매출액(원)'
        cols[-3] = '광고비(원)' 
        cols[-4] = '클릭수'
        cols[-5] = '노출수'
        cols[0] = '날짜'
        df.columns = cols
        msg = f"⚠️ 비표준({col_count}열) -> 스마트 매핑 적용"

    # 3. 데이터 형변환
    target_cols = ['광고비(원)', '전환매출액(원)', '노출수', '클릭수']
    missing = [c for c in target_cols if c not in df.columns]
    if missing:
        raise ValueError(f"필수 데이터 누락: {missing}")

    for c in target_cols:
        df[c] = df[c].astype(str).str.replace(',', '').str.replace(' ', '')
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # -------------------------------------------------------------
    # [UI 개선] 대문짝만했던 로그를 '미리보기'로 대체
    # -------------------------------------------------------------
    with st.expander(f"🔍 분석 결과 미리보기 ({msg})", expanded=True):
        st.caption("시스템이 인식한 데이터 구조입니다. 이상이 없는지 확인하세요.")
        st.dataframe(df.head(3)) # 깔끔하게 표로만 보여줌

    # 4. 좀비 필터링
    cond = ((df['광고비(원)'] >= 5000) & (df['전환매출액(원)'] == 0)) | \
           ((df['노출수'] >= 100) & (df['클릭수'] == 0))
           
    zombies = df[cond].copy()
    
    # 디스플레이용 컬럼 선택
    display_cols = ['날짜', '키워드명', '광고비(원)', '전환매출액(원)', '노출수', '클릭수']
    final_cols = [c for c in display_cols if c in zombies.columns]
    
    return zombies[final_cols if final_cols else zombies.columns]

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"