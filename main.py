import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from pathlib import Path

st.set_page_config(page_title="남양주시 사고 대시보드", layout="wide")

page = st.sidebar.radio("◾ 메뉴", ["지도 보기", "통계 보기"])

def load_template(fp):
    return Path(fp).read_text(encoding="utf-8")

if page == "지도 보기":
    # 1) HTML 템플릿 불러오기
    tpl = load_template("index.html")

    # 2) CSV → DataFrame → JSON
    df = pd.read_csv("accident.csv", encoding="utf-8")
    df = df.dropna(subset=["위도","경도"])
    acc_json = df.to_dict(orient="records")

    # 3) 템플릿에 인라인
    html = tpl.replace("{{ACCIDENT_DATA}}",
                       json.dumps(acc_json, ensure_ascii=False))

    st.markdown("## 📍 사고 + 보행등 통합 지도", unsafe_allow_html=True)
    components.html(html, height=800, scrolling=True)

else:
    # 통계 페이지도 같은 식으로 inline JSON 혹은 streamlit-native 로…
    html = load_template("accident_dashboard.html")
    st.markdown("## 📊 남양주시 사고 통계", unsafe_allow_html=True)
    components.html(html, height=600, scrolling=True)
