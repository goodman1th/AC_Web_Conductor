import streamlit as st
import datetime
import google.generativeai as genai
from io import BytesIO
import pandas as pd

# 모듈 연결
try:
    from config import load_config, save_config
except ImportError:
    st.error("🚨 'config.py' 파일이 없습니다.")
    st.stop()

from utils import read_uploaded_file, get_system_prompt, analyze_zombie_products, generate_kill_list_filename
from naver_api import download_naver_report

# ==========================================
# [SYSTEM] 페이지 설정
# ==========================================
st.set_page_config(
    page_title="AC Team Web Conductor v2.6",
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

# ==========================================
# [UI] 사이드바 (설정)
# ==========================================
with st.sidebar:
    st.header("⚙️ 시스템 통제실")
    with st.form("config_form"):
        st.subheader("🔑 Brain & Body")
        cur_key = st.session_state.master_config.get("GOOGLE_API_KEY", "")
        new_key = st.text_input("Google API Key", value=cur_key, type="password")
        
        st.caption("네이버 계정 관리")
        c1, c2 = st.columns(2)
        n_alias = c1.text_input("별칭")
        n_id = c2.text_input("ID")
        n_acc = st.text_input("Access Key", type="password")
        n_sec = st.text_input("Secret Key", type="password")
        
        if st.form_submit_button("💾 설정 저장"):
            st.session_state.master_config["GOOGLE_API_KEY"] = new_key
            if n_alias and n_id and n_acc:
                if "NAVER_ACCOUNTS" not in st.session_state.master_config:
                    st.session_state.master_config["NAVER_ACCOUNTS"] = {}
                st.session_state.master_config["NAVER_ACCOUNTS"][n_alias] = {
                    "id": n_id, "key": n_access, "secret": n_sec
                }
            save_config(st.session_state.master_config)
            st.success("저장 완료")

# ==========================================
# [UI] 메인 스테이지
# ==========================================
st.title("🏯 AC Team: Web Conductor v2.6")

tab1, tab2, tab4 = st.tabs(["💬 작전 회의실", "📊 실행실 (Naver API)", "💀 분석실 (X-Ray)"])

# [Tab 1] 작전 회의실
with tab1:
    c1, c2 = st.columns([1, 4])
    with c1:
        st.session_state.current_role = st.selectbox("🗣️ 소환 대상", 
            ["AC김시율 (Director)", "PM (Project Manager)", "Architect (설계자)", "Executor (수행자)", "Scribe (서기)"])
    
    chat_box = st.container(height=400)
    with chat_box:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    
    if prompt := st.chat_input("지시 사항 입력..."):
        if not st.session_state.master_config.get("GOOGLE_API_KEY"):
            st.error("구글 키 필요")
        else:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with chat_box.chat_message("user"): st.markdown(prompt)
            with chat_box.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        genai.configure(api_key=st.session_state.master_config["GOOGLE_API_KEY"])
                        model = genai.GenerativeModel('gemini-2.0-flash-exp', system_instruction=get_system_prompt(st.session_state.current_role))
                        res = model.generate_content(prompt)
                        st.markdown(res.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                    except Exception as e: st.error(e)

# [Tab 2] 실행실
with tab2:
    st.subheader("Naver 검색광고 리포트 추출")
    accounts = st.session_state.master_config.get("NAVER_ACCOUNTS", {})
    if not accounts: st.warning("계정 없음")
    else:
        acc_name = st.selectbox("대상 계정", list(accounts.keys()))
        if st.button("🚀 리포트 추출"):
            try:
                with st.spinner("추출 중..."):
                    df, stat_dt = download_naver_report(accounts[acc_name])
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
                    st.success(f"✅ {len(df)}건 확보")
                    st.download_button(f"📥 다운로드", out.getvalue(), file_name=f"Report_{stat_dt}.xlsx")
            except Exception as e: st.error(f"실패: {e}")

# [Tab 4] 분석실 (X-Ray 기능 추가)
with tab4:
    st.subheader("💀 좀비 상품 살생부 (X-Ray Mode)")
    st.info("💡 파일을 업로드하면, 분석 전에 **내용을 먼저 보여드립니다.**")
    
    u_kill = st.file_uploader("리포트 업로드 (Excel/CSV)", type=['xlsx', 'csv'])
    
    if u_kill:
        try:
            # 1. 일단 읽어서 보여주기 (X-Ray)
            st.markdown("### 🔍 파일 엑스레이 (Raw Data Preview)")
            
            # 확장자에 따라 읽기
            if u_kill.name.endswith('csv'):
                try:
                    df_raw = pd.read_csv(u_kill, encoding='utf-8')
                except:
                    u_kill.seek(0)
                    df_raw = pd.read_csv(u_kill, encoding='cp949')
            else:
                df_raw = pd.read_excel(u_kill)
            
            # 날것의 데이터 표시 (상위 20행)
            st.dataframe(df_raw.head(20))
            st.caption(f"👆 이게 컴퓨터가 보는 파일의 실제 모습입니다. (총 {len(df_raw)}행)")
            
            st.divider()
            
            # 2. 분석 실행 버튼
            if st.button("🔪 이 데이터로 살생부 분석 실행", type="primary"):
                # 여기서 utils의 분석기 호출
                zombies = analyze_zombie_products(df_raw)
                cnt = len(zombies)
                
                if cnt > 0:
                    st.error(f"🚨 {cnt}개 좀비 발견!")
                    st.dataframe(zombies)
                    out_z = BytesIO()
                    with pd.ExcelWriter(out_z, engine='xlsxwriter') as writer: zombies.to_excel(writer, index=False)
                    st.download_button("💀 살생부 다운로드", out_z.getvalue(), file_name=generate_kill_list_filename())
                else:
                    st.balloons(); st.success("클린합니다!")
                    
        except Exception as e:
            st.error(f"❌ 읽기 실패: {e}")