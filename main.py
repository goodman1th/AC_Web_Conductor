import streamlit as st
import datetime
import google.generativeai as genai
from io import BytesIO
import pandas as pd

# 모듈 연결 (config가 없으면 에러 방지)
try:
    from config import load_config, save_config
except ImportError:
    st.error("🚨 'config.py' 파일이 없습니다. 파일이 누락되지 않았는지 확인해주세요.")
    st.stop()

from utils import read_uploaded_file, get_system_prompt, analyze_zombie_products, generate_kill_list_filename
from naver_api import download_naver_report

# ==========================================
# [SYSTEM] 페이지 설정
# ==========================================
st.set_page_config(
    page_title="AC Team Web Conductor v2.7",
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
        st.subheader("🔑 Brain & Body")
        cur_key = st.session_state.master_config.get("GOOGLE_API_KEY", "")
        new_key = st.text_input("Google API Key", value=cur_key, type="password")
        
        st.divider()
        st.caption("네이버 계정 관리")
        c1, c2 = st.columns(2)
        n_alias = c1.text_input("별칭 (예: 1호점)")
        n_id = c2.text_input("ID")
        n_acc = st.text_input("Access Key", type="password")
        n_sec = st.text_input("Secret Key", type="password")
        
        if st.form_submit_button("💾 설정 저장"):
            st.session_state.master_config["GOOGLE_API_KEY"] = new_key
            if n_alias and n_id and n_acc:
                if "NAVER_ACCOUNTS" not in st.session_state.master_config:
                    st.session_state.master_config["NAVER_ACCOUNTS"] = {}
                st.session_state.master_config["NAVER_ACCOUNTS"][n_alias] = {
                    "id": n_id, "key": n_acc, "secret": n_sec
                }
            save_config(st.session_state.master_config)
            st.success("저장 완료")
    
    # 계정 삭제 기능
    accounts = st.session_state.master_config.get("NAVER_ACCOUNTS", {})
    if accounts:
        del_target = st.selectbox("계정 삭제", ["선택 안함"] + list(accounts.keys()))
        if del_target != "선택 안함" and st.button("🗑️ 삭제"):
            del st.session_state.master_config["NAVER_ACCOUNTS"][del_target]
            save_config(st.session_state.master_config)
            st.rerun()

# ==========================================
# [UI] 메인 스테이지
# ==========================================
st.title("🏯 AC Team: Web Conductor v2.7")
st.caption("Update: 📥 Custom Column Selector Added")

tab1, tab2, tab4 = st.tabs(["💬 작전 회의실", "📊 실행실 (Naver API)", "💀 분석실 (Guillotine)"])

# [Tab 1] 작전 회의실
with tab1:
    c1, c2 = st.columns([1, 4])
    with c1:
        st.session_state.current_role = st.selectbox("🗣️ 소환 대상", 
            ["AC김시율 (Director)", "PM (Project Manager)", "Architect (설계자)", "Executor (수행자)", "Scribe (서기)"])
    
    chat_box = st.container(height=400)
    with chat_box:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
    
    if prompt := st.chat_input("지시 사항 입력..."):
        if not st.session_state.master_config.get("GOOGLE_API_KEY"): st.error("구글 키 필요")
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
    if not accounts: st.warning("등록된 계정이 없습니다.")
    else:
        acc_name = st.selectbox("대상 계정", list(accounts.keys()))
        if st.button("🚀 리포트 추출"):
            try:
                with st.spinner("추출 중..."):
                    df, stat_dt = download_naver_report(accounts[acc_name])
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
                    st.success(f"✅ {len(df)}건 확보")
                    st.download_button(f"📥 전체 다운로드", out.getvalue(), file_name=f"Report_{stat_dt}.xlsx")
            except Exception as e: st.error(f"실패: {e}")

# [Tab 4] 분석실 (컬럼 선택 기능 추가)
with tab4:
    st.subheader("💀 좀비 상품 살생부 (Custom Export)")
    u_kill = st.file_uploader("리포트 업로드 (Excel/CSV)", type=['xlsx', 'csv'])
    
    if u_kill and st.button("🔪 분석 실행", type="primary"):
        try:
            # 1. 파일 읽기 (CSV/Excel 처리)
            if u_kill.name.endswith('csv'):
                try: df_raw = pd.read_csv(u_kill, encoding='utf-8')
                except: u_kill.seek(0); df_raw = pd.read_csv(u_kill, encoding='cp949')
            else:
                df_raw = pd.read_excel(u_kill)

            # 2. 분석 실행 (utils 호출)
            zombies = analyze_zombie_products(df_raw)
            cnt = len(zombies)
            
            if cnt > 0:
                st.error(f"🚨 {cnt}개의 좀비 상품이 발견되었습니다!")
                
                # --- [NEW] 컬럼 선택 기능 ---
                st.divider()
                st.markdown("##### 📥 다운로드 옵션")
                
                all_cols = zombies.columns.tolist()
                # 기본적으로 선택되어 있을 컬럼들 (너무 많으면 복잡하니까 중요 항목만 자동 선택)
                default_cols = [c for c in all_cols if any(k in str(c) for k in ['ID', '키워드', '광고비', '노출', '클릭', '매출'])]
                if not default_cols: default_cols = all_cols # 못 찾으면 전체 선택
                
                # 멀티 셀렉트 위젯
                selected_cols = st.multiselect(
                    "💾 파일에 저장할 항목을 골라주세요:",
                    options=all_cols,
                    default=default_cols
                )
                
                if not selected_cols:
                    st.warning("최소 1개 이상의 컬럼을 선택해야 다운로드할 수 있습니다.")
                else:
                    # 선택한 컬럼만 필터링
                    df_final = zombies[selected_cols]
                    
                    # 미리보기 제공
                    st.caption(f"미리보기 ({len(selected_cols)}개 열 선택됨)")
                    st.dataframe(df_final.head())
                    
                    # 다운로드 버튼
                    out_z = BytesIO()
                    with pd.ExcelWriter(out_z, engine='xlsxwriter') as writer:
                        df_final.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="💀 선택 항목만 다운로드 (Kill List)",
                        data=out_z.getvalue(),
                        file_name=generate_kill_list_filename(),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.balloons(); st.success("클린합니다! 좀비가 없습니다.")
                
        except Exception as e:
            st.error(f"분석 오류: {e}")