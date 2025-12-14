import streamlit as st
import pandas as pd
from io import BytesIO
import google.generativeai as genai
try: from config import load_config, save_config
except: st.error("config.py 누락"); st.stop()
from utils import analyze_zombie_products, generate_kill_list_filename
from naver_api import download_naver_report

st.set_page_config(page_title="AC Team Web Conductor v2.8", layout="wide")

if 'master_config' not in st.session_state: st.session_state.master_config = load_config()

with st.sidebar:
    st.header("⚙️ 통제실")
    with st.form("conf"):
        k = st.text_input("Google Key", value=st.session_state.master_config.get("GOOGLE_API_KEY",""), type="password")
        if st.form_submit_button("저장"):
            st.session_state.master_config["GOOGLE_API_KEY"] = k
            save_config(st.session_state.master_config); st.success("저장됨")

st.title("🏯 AC Team: Web Conductor v2.8")
tab1, tab2, tab4 = st.tabs(["💬 작전회의", "📊 실행실", "💀 분석실"])

with tab2:
    st.subheader("리포트 추출")
    accs = st.session_state.master_config.get("NAVER_ACCOUNTS", {})
    if accs:
        tgt = st.selectbox("계정", list(accs.keys()))
        if st.button("🚀 추출"):
            df, dt = download_naver_report(accs[tgt])
            out = BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as w: df.to_excel(w, index=False)
            st.download_button("📥 다운로드", out.getvalue(), file_name=f"Report_{dt}.xlsx")

with tab4:
    st.subheader("💀 좀비 분석 (X-Ray & Select)")
    up = st.file_uploader("파일 업로드", type=['xlsx', 'csv'])
    if up:
        st.markdown("##### 🔍 X-Ray 미리보기")
        try:
            if up.name.endswith('csv'): 
                try: df = pd.read_csv(up)
                except: up.seek(0); df = pd.read_csv(up, encoding='cp949')
            else: df = pd.read_excel(up)
            st.dataframe(df.head())
            
            if st.button("🔪 분석 실행"):
                zom = analyze_zombie_products(df)
                if not zom.empty:
                    st.error(f"🚨 {len(zom)}개 좀비 발견!")
                    sel = st.multiselect("💾 저장할 컬럼 선택", zom.columns.tolist(), default=zom.columns.tolist())
                    if sel:
                        out = BytesIO()
                        with pd.ExcelWriter(out, engine='xlsxwriter') as w: zom[sel].to_excel(w, index=False)
                        st.download_button("💀 살생부 다운로드", out.getvalue(), file_name=generate_kill_list_filename())
                else: st.success("클린합니다.")
        except Exception as e: st.error(f"오류: {e}")