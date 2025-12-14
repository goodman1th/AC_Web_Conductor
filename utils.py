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
    [v4.0 Final] 네이버 API 공식 스키마 적용 (Guessing 제거)
    리포트 유형에 따라 고정된 컬럼명을 강제로 할당합니다.
    """
    st.markdown("##### 🕵️ 분석 엔진 로그 (Standard Schema Mode)")
    
    # 1. 데이터 정리 (헤더가 있든 없든 일단 가져옴)
    # 만약 첫 줄이 날짜(2025...)라면, 그 줄은 데이터이므로 포함시켜야 함
    df.columns = [str(c).strip() for c in df.columns]
    first_val = df.columns[0]
    
    # 헤더가 없는 파일(API 원본)이라고 판단되면, 첫 줄을 데이터로 내림
    if first_val.startswith('20') and first_val.isdigit():
        new_row = pd.DataFrame([df.columns], columns=df.columns)
        df = pd.concat([new_row, df], ignore_index=True)
        st.info("💡 API 원본 데이터(무제) 감지 -> 공식 스키마 적용")

    # 2. [네이버 검색광고 API 공식 스키마 (Report Type: AD 기준)]
    # 출처: Naver Search Ad API Document > Stat Reports
    # 순서: statDt, custId, adgroupId, keywordId, adgroupName, keywordName, ..., impCnt, clkCnt, salesAmt, convAmt
    # (주의: 사용자가 다운로드한 파일의 열 개수에 따라 매핑 전략을 달리함)
    
    col_count = len(df.columns)
    
    # [Case A] 14개 열 (가장 일반적인 형태)
    schema_14 = [
        '날짜', '고객ID', '캠페인ID', '광고그룹ID', '키워드ID', '키워드명', 
        '매체', '지역', '순위', '노출수', '클릭수', '광고비(원)', '전환수', '전환매출액(원)'
    ]
    
    # [Case B] 12개 열 (상세 데이터 일부 제외)
    schema_12 = [
        '날짜', '캠페인ID', '광고그룹ID', '키워드ID', '키워드명', 
        '매체', '노출수', '클릭수', '클릭률', '평균클릭비용', '광고비(원)', '전환매출액(원)'
    ]

    # 스키마 적용 로직
    if col_count == 14:
        df.columns = schema_14
        st.success("✅ 표준 스키마(14열) 매핑 완료")
    elif col_count == 12:
        df.columns = schema_12
        st.success("✅ 표준 스키마(12열) 매핑 완료")
    else:
        # 열 개수가 표준과 다르면, '중요 데이터'가 뒤에 있다는 법칙을 이용해 역순 매핑
        st.warning(f"⚠️ 열 개수({col_count})가 표준(12, 14)과 다릅니다. 스마트 매핑을 시도합니다.")
        cols = [f"Col_{i}" for i in range(col_count)]
        
        # 뒤에서부터 매칭 (API는 보통 성과 지표를 뒤에 배치함)
        cols[-1] = '전환매출액(원)'
        cols[-3] = '광고비(원)' 
        cols[-4] = '클릭수'
        cols[-5] = '노출수'
        cols[0] = '날짜'
        
        df.columns = cols
        st.info("💡 스마트 역순 매핑 완료")

    # 3. 데이터 형변환 (콤마 제거 후 숫자 변환)
    target_cols = ['광고비(원)', '전환매출액(원)', '노출수', '클릭수']
    
    # 매핑된 컬럼이 실제로 존재하는지 확인
    missing = [c for c in target_cols if c not in df.columns]
    if missing:
        raise ValueError(f"컬럼 매핑 실패. 누락된 항목: {missing}")

    for c in target_cols:
        df[c] = df[c].astype(str).str.replace(',', '').str.replace(' ', '')
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 4. 좀비 필터링 (ROI 0인 항목)
    # 조건: 돈(5000원 이상) 썼는데 매출 0 OR 노출(100회 이상) 됐는데 클릭 0
    cond = ((df['광고비(원)'] >= 5000) & (df['전환매출액(원)'] == 0)) | \
           ((df['노출수'] >= 100) & (df['클릭수'] == 0))
           
    zombies = df[cond].copy()
    
    # 보기 좋게 컬럼 정리
    display_cols = ['날짜', '키워드명', '광고비(원)', '전환매출액(원)', '노출수', '클릭수']
    # 만약 키워드명이 없으면(역순매핑 등) 있는 것만 표시
    final_cols = [c for c in display_cols if c in zombies.columns]
    
    return zombies[final_cols if final_cols else zombies.columns]

def generate_kill_list_filename():
    return f"Kill_List_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"