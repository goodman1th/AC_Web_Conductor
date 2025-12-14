import streamlit as st
import datetime
import google.generativeai as genai
from io import BytesIO
import pandas as pd

# 모듈 임포트 (같은 폴더에 있어야 함)
from utils import read_uploaded_file, get_system_prompt, analyze_zombie_products, generate_kill_list_filename, log_event
from naver_api import download_naver_report
from config import load_config, save_config

# ==========================================
# [SYSTEM] 페이지 설정
# ==========================================
st.set_page_config(
    page_title="AC Team Web Conductor v2.3",
    page_icon="🏯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# [STATE] 상태 초기화
# ==========================================
# 1. 마스터 설정 로드 (파일에서 불러옴)
if 'master_config' not in st.session_state:
    st.session_state.master_config = load_config()

if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = []

if 'current_role' not in st.session_state: 
    st.session_state.current_role = "AC김시율 (Director)"

if 'logs' not in st.session_state:
    st.session_state.logs = []

# ==========================================
# [UI] 사이드바: 통합 키 관리소
# ==========================================
with st.sidebar:
    st.header("⚙️ 시스템 통제실")
    
    # [설정 저장] 버튼을 위한 폼
    with st.form("config_form"):
        st.subheader("🔑 Brain (Google)")
        
        # 구글 키 입력
        current_google_key = st.session_state.master_config.get("GOOGLE_API_KEY", "")
        new_google_key = st.text_input("Google API Key", value=current_google_key, type="password")

        st.divider()
        st.subheader("🏦 Body (Naver Accounts)")
        
        # 네이버 계정 추가 UI (간소화)
        col1, col2 = st.columns(2)
        new_alias = col1.text_input("새 계정 별칭 (예: 1호점)")
        new_id = col2.text_input("Customer ID")
        new_key = st.text_input("Access Key", type="password")
        new_secret = st.text_input("Secret Key", type="password")
        
        # 저장 버튼 (이걸 눌러야 파일에 저장됨)
        if st.form_submit_button("💾 전체 설정 저장 (Save Config)"):
            # 구글 키 업데이트
            st.session_state.master_config["GOOGLE_API_KEY"] = new_google_key
            
            # 네이버 계정 추가 로직
            if new_alias and new_id and new_key:
                st.session_state.master_config["NAVER_ACCOUNTS"][new_alias] = {
                    "id": new_id, "key": new_key, "secret": new_secret
                }
            
            # 실제 파일 저장 (config.py 호출)
            if save_config(st.session_state.master_config):
                st.success("설정이 'config.json'에 안전하게 저장되었습니다.")
                log_event("설정 파일 업데이트 완료")
            else:
                st.error("설정 저장 실패")
    
    # 등록된 계정 목록 삭제 기능
    if st.session_state.master_config.get("NAVER_ACCOUNTS"):
        st.divider()
        st.caption(f"등록된 계정: {len(st.session_state.master_config['NAVER_ACCOUNTS'])}개")
        del_target = st.selectbox("계정 삭제", ["선택 안함"] + list(st.session_state.master_config["NAVER_ACCOUNTS"].keys()))
        
        if del_target != "선택 안함" and st.button("🗑️ 삭제 실행"):
            del st.session_state.master_config["NAVER_ACCOUNTS"][del_target]
            save_config(st.session_state.master_config) # 삭제 후 즉시 저장
            st.rerun()

# ==========================================
# [UI] 메인 스테이지
# ==========================================
st.title("🏯 AC Team: Web Conductor v2.3")
st.caption("Status: 🟢 System Online | 🧩 Modular Architecture Applied")

# 탭 구성
tab1, tab2, tab4 = st.tabs(["💬 작전 회의실", "📊 실행실 (Naver API)", "💀 분석실 (Guillotine)"])

# -------------------------------------------------------
# [Tab 1] 작전 회의실
# -------------------------------------------------------
with tab1:
    col1, col2 = st.columns([1, 4])
    with col1:
        st.session_state.current_role = st.selectbox(
            "🗣️ 대화/명령 주체", 
            ["AC김시율 (Director)", "PM (Project Manager)", "Architect (설계자)", "Executor (수행자)", "Scribe (서기)"]
        )

    chat_container = st.container(height=500)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    uploaded_file = st.file_uploader("자료 첨부", type=['xlsx', 'csv', 'txt', 'py', 'json'], label_visibility="collapsed")
    
    if prompt := st.chat_input("지시 사항 입력..."):
        if not st.session_state.master_config["GOOGLE_API_KEY"]:
            st.error("🚨 구글 키가 없습니다. 사이드바에서 설정 후 저장해주세요.")
        else:
            display_msg = prompt
            full_prompt = prompt
            
            if uploaded_file:
                file_content = read_uploaded_file(uploaded_file)
                full_prompt = f"--- [첨부 파일] ---\n{file_content}\n----------------\n\n[질문]\n{prompt}"
                display_msg = f"📎 **[{uploaded_file.name}]**\n\n{prompt}"

            st.session_state.chat_history.append({"role": "user", "content": display_msg})
            with chat_container.chat_message("user"):
                st.markdown(display_msg)

            with chat_container.chat_message("assistant"):
                with st.spinner("Think..."):
                    try:
                        sys_inst = get_system_prompt(st.session_state.current_role)
                        genai.configure(api_key=st.session_state.master_config["GOOGLE_API_KEY"])
                        model = genai.GenerativeModel('gemini-2.0-flash-exp', system_instruction=sys_inst)
                        response = model.generate_content(full_prompt)
                        st.markdown(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error(f"통신 오류: {e}")

# -------------------------------------------------------
# [Tab 2] 실행실 (네이버 리포트)
# -------------------------------------------------------
with tab2:
    st.subheader("Naver 검색광고 리포트 추출")
    
    accounts = st.session_state.master_config.get("NAVER_ACCOUNTS", {})
    if not accounts:
        st.warning("등록된 계정이 없습니다. 사이드바에서 추가하세요.")
    else:
        target_acc_name = st.selectbox("대상 계정", list(accounts.keys()))
        target_acc = accounts[target_acc_name]
        
        if st.button("🚀 리포트 추출 및 다운로드", type="primary"):
            try:
                with st.spinner(f"[{target_acc_name}] 리포트 추출 중..."):
                    # naver_api 모듈 호출
                    df, stat_dt = download_naver_report(target_acc)
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False)
                    data = output.getvalue()
                    
                    st.success(f"✅ 성공! {len(df)}개 데이터 확보.")
                    st.download_button(f"📥 {target_acc_name}_{stat_dt}.xlsx", data, file_name=f"Report_{target_acc_name}_{stat_dt}.xlsx")

            except Exception as e:
                st.error(f"작업 실패: {e}")

# -------------------------------------------------------
# [Tab 4] 분석실 (Guillotine)
# -------------------------------------------------------
with tab4:
    st.subheader("💀 좀비 상품 살생부 작성")
    st.info("💡 네이버 리포트 엑셀 파일을 업로드하면, '돈만 먹는 상품'을 자동으로 걸러냅니다.")
    
    uploaded_kill_file = st.file_uploader("분석할 리포트 업로드 (Excel)", type=['xlsx'])
    
    if uploaded_kill_file and st.button("🔪 살생부 분석 실행", type="primary"):
        try:
            df = pd.read_excel(uploaded_kill_file)
            # utils 모듈 호출
            zombies = analyze_zombie_products(df)
            count = len(zombies)
            
            if count > 0:
                st.error(f"🚨 총 {count}개의 좀비 상품 발견!")
                st.dataframe(zombies)
                
                output_z = BytesIO()
                with pd.ExcelWriter(output_z, engine='xlsxwriter') as writer:
                    zombies.to_excel(writer, index=False)
                data_z = output_z.getvalue()
                
                # utils 모듈 호출
                filename = generate_kill_list_filename()
                
                st.download_button(
                    label="💀 살생부(Kill List) 다운로드",
                    data=data_z,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.balloons()
                st.success("✨ 축하합니다! 좀비 상품이 없습니다.")
                
        except Exception as e:
            st.error(f"분석 오류: {e}")