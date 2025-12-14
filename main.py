import streamlit as st
import datetime
import google.generativeai as genai
from io import BytesIO
import pandas as pd

# 모듈 연결 (config가 없으면 에러남)
try:
    from config import load_config, save_config
except ImportError:
    st.error("🚨 'config.py' 파일이 없습니다. 코드를 확인해주세요.")
    st.stop()

from utils import read_uploaded_file, get_system_prompt, analyze_zombie_products, generate_kill_list_filename, log_event
from naver_api import download_naver_report

# ==========================================
# [SYSTEM] 페이지 설정
# ==========================================
st.set_page_config(
    page_title="AC Team Web Conductor v2.5",
    page_icon="🏯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# [STATE] 상태 초기화
# ==========================================
if 'master_config' not in st.session_state:
    st.session_state.master_config = load_config()

if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'current_role' not in st.session_state: st.session_state.current_role = "AC김시율 (Director)"
if 'logs' not in st.session_state: st.session_state.logs = []

# ==========================================
# [UI] 사이드바
# ==========================================
with st.sidebar:
    st.header("⚙️ 시스템 통제실")
    
    with st.form("config_form"):
        st.subheader("🔑 Brain (Google)")
        cur_key = st.session_state.master_config.get("GOOGLE_API_KEY", "")
        new_key = st.text_input("Google API Key", value=cur_key, type="password")
        
        st.divider()
        st.subheader("🏦 Body (Naver Accounts)")
        
        c1, c2 = st.columns(2)
        n_alias = c1.text_input("별칭 (예: 1호점)")
        n_id = c2.text_input("Customer ID")
        n_access = st.text_input("Access Key", type="password")
        n_secret = st.text_input("Secret Key", type="password")
        
        if st.form_submit_button("💾 설정 저장 (Save)"):
            st.session_state.master_config["GOOGLE_API_KEY"] = new_key
            if n_alias and n_id and n_access:
                if "NAVER_ACCOUNTS" not in st.session_state.master_config:
                    st.session_state.master_config["NAVER_ACCOUNTS"] = {}
                st.session_state.master_config["NAVER_ACCOUNTS"][n_alias] = {
                    "id": n_id, "key": n_access, "secret": n_secret
                }
            
            if save_config(st.session_state.master_config):
                st.success("설정이 저장되었습니다.")
            else:
                st.error("설정 저장 실패")
    
    # 계정 목록 및 삭제
    accounts = st.session_state.master_config.get("NAVER_ACCOUNTS", {})
    if accounts:
        st.divider()
        st.caption(f"등록된 계정: {len(accounts)}개")
        del_target = st.selectbox("계정 삭제", ["선택 안함"] + list(accounts.keys()))
        if del_target != "선택 안함" and st.button("🗑️ 삭제"):
            del st.session_state.master_config["NAVER_ACCOUNTS"][del_target]
            save_config(st.session_state.master_config)
            st.rerun()

# ==========================================
# [UI] 메인 스테이지
# ==========================================
st.title("🏯 AC Team: Web Conductor v2.5")
st.caption("Status: 🟢 System Online | 🧩 Modular System Restored")

tab1, tab2, tab4 = st.tabs(["💬 작전 회의실", "📊 실행실 (Naver API)", "💀 분석실 (Guillotine)"])

# [Tab 1] 작전 회의실
with tab1:
    c1, c2 = st.columns([1, 4])
    with c1:
        st.session_state.current_role = st.selectbox("🗣️ 소환 대상", 
            ["AC김시율 (Director)", "PM (Project Manager)", "Architect (설계자)", "Executor (수행자)", "Scribe (서기)"])
    
    chat_box = st.container(height=500)
    with chat_box:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    
    up_file = st.file_uploader("자료 첨부", type=['xlsx','csv','txt','py','json'], label_visibility="collapsed")
    
    if prompt := st.chat_input("지시 사항 입력..."):
        if not st.session_state.master_config.get("GOOGLE_API_KEY"):
            st.error("🚨 구글 키가 없습니다. 사이드바에서 설정 후 저장해주세요.")
        else:
            full_prompt = prompt
            display_msg = prompt
            if up_file:
                content = read_uploaded_file(up_file)
                full_prompt = f"--- [첨부파일] ---\n{content}\n----------------\n[질문]\n{prompt}"
                display_msg = f"📎 **[{up_file.name}]**\n\n{prompt}"
            
            st.session_state.chat_history.append({"role": "user", "content": display_msg})
            with chat_box.chat_message("user"):
                st.markdown(display_msg)
            
            with chat_box.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        genai.configure(api_key=st.session_state.master_config["GOOGLE_API_KEY"])
                        sys_inst = get_system_prompt(st.session_state.current_role)
                        model = genai.GenerativeModel('gemini-2.0-flash-exp', system_instruction=sys_inst)
                        res = model.generate_content(full_prompt)
                        st.markdown(res.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                    except Exception as e:
                        st.error(f"오류: {e}")

# [Tab 2] 실행실
with tab2:
    st.subheader("Naver 검색광고 리포트 추출")
    if not accounts:
        st.warning("등록된 계정이 없습니다.")
    else:
        acc_name = st.selectbox("대상 계정", list(accounts.keys()))
        if st.button("🚀 리포트 추출"):
            try:
                with st.spinner(f"[{acc_name}] 추출 중..."):
                    df, stat_dt = download_naver_report(accounts[acc_name])
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False)
                    st.success(f"✅ {len(df)}개 데이터 확보")
                    st.download_button(f"📥 {acc_name}_{stat_dt}.xlsx", out.getvalue(), file_name=f"Report_{stat_dt}.xlsx")
            except Exception as e:
                st.error(f"실패: {e}")

# [Tab 4] 분석실
with tab4:
    st.subheader("💀 좀비 상품 살생부 작성")
    u_kill = st.file_uploader("리포트 업로드 (Excel)", type=['xlsx'])
    if u_kill and st.button("🔪 분석 실행"):
        try:
            df = pd.read_excel(u_kill)
            zombies = analyze_zombie_products(df)
            cnt = len(zombies)
            if cnt > 0:
                st.error(f"🚨 {cnt}개 좀비 발견!")
                st.dataframe(zombies)
                out_z = BytesIO()
                with pd.ExcelWriter(out_z, engine='xlsxwriter') as writer:
                    zombies.to_excel(writer, index=False)
                st.download_button("💀 살생부 다운로드", out_z.getvalue(), file_name=generate_kill_list_filename())
            else:
                st.balloons(); st.success("클린합니다!")
        except Exception as e:
            st.error(f"분석 오류: {e}")