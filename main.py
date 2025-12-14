import streamlit as st
import datetime
import google.generativeai as genai
from io import BytesIO
import pandas as pd

# --------------------------------------------------------------------------
# [Module Connection] 필수 모듈 로드
# --------------------------------------------------------------------------
try:
    from config import load_config, save_config
except ImportError:
    st.error("🚨 [System Critical] 'config.py' 파일이 누락되었습니다. 파일을 확인해주세요.")
    st.stop()

from utils import read_uploaded_file, get_system_prompt, analyze_zombie_products, generate_kill_list_filename
from naver_api import download_naver_report

# ==========================================
# [SYSTEM] 페이지 기본 설정
# ==========================================
st.set_page_config(
    page_title="AC Team Web Conductor v3.0",
    page_icon="🏯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# [STATE] 세션 상태 초기화 (Session State)
# ==========================================
if 'master_config' not in st.session_state:
    st.session_state.master_config = load_config()

if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = []

if 'current_role' not in st.session_state: 
    st.session_state.current_role = "AC김시율 (Director)"

# ==========================================
# [UI] 사이드바: 통합 제어 센터
# ==========================================
with st.sidebar:
    st.header(⚙️ 시스템 통제실")
    st.markdown("---")
    
    # 1. Google Brain 설정
    with st.expander("🔑 Brain (Google API)", expanded=True):
        current_google_key = st.session_state.master_config.get("GOOGLE_API_KEY", "")
        new_google_key = st.text_input("API Key 입력", value=current_google_key, type="password")
        
        if st.button("구글 키 저장"):
            st.session_state.master_config["GOOGLE_API_KEY"] = new_google_key
            save_config(st.session_state.master_config)
            st.success("Brain 연결 완료")

    # 2. Naver Body 설정
    with st.expander("🏦 Body (Naver Ad Accounts)", expanded=False):
        with st.form("naver_account_form", clear_on_submit=True):
            st.caption("새 계정 추가")
            col_a, col_b = st.columns(2)
            input_alias = col_a.text_input("별칭 (예: 1호점)")
            input_id = col_b.text_input("Customer ID")
            input_key = st.text_input("Access Key", type="password")
            input_secret = st.text_input("Secret Key", type="password")
            
            if st.form_submit_button("계정 추가"):
                if input_alias and input_id and input_key:
                    if "NAVER_ACCOUNTS" not in st.session_state.master_config:
                        st.session_state.master_config["NAVER_ACCOUNTS"] = {}
                    
                    st.session_state.master_config["NAVER_ACCOUNTS"][input_alias] = {
                        "id": input_id, "key": input_key, "secret": input_secret
                    }
                    save_config(st.session_state.master_config)
                    st.success(f"[{input_alias}] 등록 완료")
                    st.rerun()

        # 계정 삭제 기능
        registered_accounts = st.session_state.master_config.get("NAVER_ACCOUNTS", {})
        if registered_accounts:
            st.divider()
            st.caption(f"등록된 계정: {len(registered_accounts)}개")
            target_to_delete = st.selectbox("삭제할 계정 선택", ["선택 안함"] + list(registered_accounts.keys()))
            
            if target_to_delete != "선택 안함":
                if st.button("🗑️ 영구 삭제"):
                    del st.session_state.master_config["NAVER_ACCOUNTS"][target_to_delete]
                    save_config(st.session_state.master_config)
                    st.warning(f"[{target_to_delete}] 삭제되었습니다.")
                    st.rerun()

# ==========================================
# [UI] 메인 스테이지
# ==========================================
st.title("🏯 AC Team: Web Conductor v3.0")
st.caption("Status: 🟢 System Online | Full Logic Restored")

# 탭 구성
tab_chat, tab_exec, tab_anal = st.tabs(["💬 작전 회의실", "📊 실행실 (Naver API)", "💀 분석실 (X-Ray & Select)"])

# -------------------------------------------------------
# [Tab 1] 작전 회의실 (Chat)
# -------------------------------------------------------
with tab_chat:
    col_role, col_dummy = st.columns([1, 4])
    with col_role:
        st.session_state.current_role = st.selectbox(
            "🗣️ 대화/명령 주체", 
            ["AC김시율 (Director)", "PM (Project Manager)", "Architect (설계자)", "Executor (수행자)", "Scribe (서기)"]
        )

    # 대화 기록 표시 영역
    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 입력 영역
    uploaded_file = st.file_uploader("참조 파일 첨부 (Context)", type=['xlsx', 'csv', 'txt', 'py', 'json'], label_visibility="collapsed")
    user_input = st.chat_input("AC팀에게 지시 사항을 입력하세요...")

    if user_input:
        if not st.session_state.master_config.get("GOOGLE_API_KEY"):
            st.error("🚨 구글 API 키가 설정되지 않았습니다. 사이드바를 확인하세요.")
        else:
            # 프롬프트 구성
            full_prompt = user_input
            display_message = user_input
            
            if uploaded_file:
                file_content = read_uploaded_file(uploaded_file)
                full_prompt = f"--- [첨부 파일: {uploaded_file.name}] ---\n{file_content}\n----------------\n\n[사용자 질문]\n{user_input}"
                display_message = f"📎 **[{uploaded_file.name}]**\n\n{user_input}"

            # 사용자 메시지 기록
            st.session_state.chat_history.append({"role": "user", "content": display_message})
            with chat_container.chat_message("user"):
                st.markdown(display_message)

            # AI 응답 생성
            with chat_container.chat_message("assistant"):
                with st.spinner(f"[{st.session_state.current_role}] 분석 중..."):
                    try:
                        genai.configure(api_key=st.session_state.master_config["GOOGLE_API_KEY"])
                        system_instruction = get_system_prompt(st.session_state.current_role)
                        model = genai.GenerativeModel('gemini-2.0-flash-exp', system_instruction=system_instruction)
                        
                        response = model.generate_content(full_prompt)
                        st.markdown(response.text)
                        
                        # AI 메시지 기록
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error(f"AI 통신 오류: {e}")

# -------------------------------------------------------
# [Tab 2] 실행실 (Naver API Report)
# -------------------------------------------------------
with tab_exec:
    st.subheader("📊 Naver 검색광고 리포트 추출")
    st.info("네이버 광고 서버에 접속하여 어제 자 리포트를 다운로드합니다.")
    
    accounts = st.session_state.master_config.get("NAVER_ACCOUNTS", {})
    if not accounts:
        st.warning("⚠️ 등록된 계정이 없습니다. 사이드바에서 계정을 추가해주세요.")
    else:
        selected_account_name = st.selectbox("대상 계정 선택", list(accounts.keys()))
        
        if st.button("🚀 리포트 추출 시작", type="primary"):
            target_account = accounts[selected_account_name]
            try:
                with st.spinner(f"[{selected_account_name}] 데이터 수신 중..."):
                    # API 호출
                    report_df, stat_date = download_naver_report(target_account)
                    
                    # 엑셀 변환
                    output_excel = BytesIO()
                    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                        report_df.to_excel(writer, index=False)
                    
                    st.success(f"✅ 추출 성공! (날짜: {stat_date}, 데이터: {len(report_df)}행)")
                    
                    st.download_button(
                        label=f"📥 리포트 다운로드 ({selected_account_name})",
                        data=output_excel.getvalue(),
                        file_name=f"Report_{selected_account_name}_{stat_date}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"작업 실패: {e}")

# -------------------------------------------------------
# [Tab 4] 분석실 (Analysis Lab)
# -------------------------------------------------------
with tab_anal:
    st.subheader("💀 좀비 상품 살생부 (Analysis & Custom Export)")
    st.markdown("""
    1. **X-Ray:** 파일을 올리면 내용을 먼저 보여줍니다. (제목줄 확인용)
    2. **Analysis:** '좀비 상품'을 자동으로 찾아냅니다.
    3. **Selector:** 원하는 컬럼만 골라서 다운로드합니다.
    """)
    
    uploaded_analyze_file = st.file_uploader("분석할 리포트 업로드 (Excel or CSV)", type=['xlsx', 'csv'])
    
    if uploaded_analyze_file:
        try:
            # 1. X-Ray 프리뷰 (파일 읽기)
            st.divider()
            st.markdown("##### 🔍 X-Ray: 파일 내용 미리보기")
            
            if uploaded_analyze_file.name.endswith('csv'):
                try:
                    df_raw = pd.read_csv(uploaded_analyze_file, encoding='utf-8')
                except UnicodeDecodeError:
                    uploaded_analyze_file.seek(0)
                    df_raw = pd.read_csv(uploaded_analyze_file, encoding='cp949')
            else:
                df_raw = pd.read_excel(uploaded_analyze_file)
            
            st.dataframe(df_raw.head())
            st.caption(f"파일 정보: {uploaded_analyze_file.name} | 총 {len(df_raw)}행")
            
            # 2. 분석 실행 버튼
            if st.button("🔪 위 데이터로 살생부 분석 실행", type="primary"):
                try:
                    # utils의 분석 함수 호출
                    zombie_df = analyze_zombie_products(df_raw)
                    zombie_count = len(zombie_df)
                    
                    if zombie_count > 0:
                        st.error(f"🚨 총 {zombie_count}개의 좀비 상품(효율 저하)이 발견되었습니다!")
                        
                        # 3. 컬럼 선택기 (Column Selector)
                        st.divider()
                        st.markdown("##### 🛒 다운로드 항목 선택 (Custom Export)")
                        
                        all_columns = zombie_df.columns.tolist()
                        
                        # 기본 선택 로직 (중요 키워드가 포함된 컬럼 자동 체크)
                        important_keywords = ['ID', '키워드', '광고비', '노출', '클릭', '매출', '비용', 'Cost', 'Sales']
                        default_selections = [col for col in all_columns if any(kw in str(col) for kw in important_keywords)]
                        if not default_selections: default_selections = all_columns
                        
                        selected_columns = st.multiselect(
                            "저장할 데이터 항목을 선택하세요:",
                            options=all_columns,
                            default=default_selections
                        )
                        
                        if selected_columns:
                            final_df = zombie_df[selected_columns]
                            
                            st.caption(f"선택된 데이터 미리보기 ({len(selected_columns)}개 열)")
                            st.dataframe(final_df.head(3))
                            
                            # 엑셀 다운로드 생성
                            output_zombie = BytesIO()
                            with pd.ExcelWriter(output_zombie, engine='xlsxwriter') as writer:
                                final_df.to_excel(writer, index=False)
                            
                            st.download_button(
                                label="💀 선택 항목만 살생부 다운로드",
                                data=output_zombie.getvalue(),
                                file_name=generate_kill_list_filename(),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.warning("⚠️ 최소 1개 이상의 컬럼을 선택해야 합니다.")
                            
                    else:
                        st.balloons()
                        st.success("✨ 축하합니다! 좀비 상품이 하나도 없습니다. 광고 효율이 매우 좋습니다.")

                except ValueError as ve:
                    st.error(f"분석 로직 오류: {ve}")
                except Exception as e:
                    st.error(f"알 수 없는 오류 발생: {e}")
                    
        except Exception as e:
            st.error(f"파일 읽기 실패: {e}")