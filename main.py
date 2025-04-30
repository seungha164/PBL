# app.py
import os
import pandas as pd
import streamlit as st
import utils
import folium
from folium.plugins import MarkerCluster
import streamlit.components.v1 as components

# 1. Streamlit UI 설정
st.set_page_config(page_title="신호등 대시보드", layout="wide")
st.title("🚦 신호등 위치 & 통계 대시보드")
st.markdown("보행자용과 차량용 신호등 통계와 위치 지도를 빠르게 확인하세요.")

# 2. 데이터 로드
df = utils.DF_BLINKER.copy()

# 3. 사이드바 필터
region = st.sidebar.text_input("🔍 지역 필터 (주소 키워드)", value="")
if region:
    df = df[df["소재지도로명주소"].str.contains(region)]
    
# 4. 통계 계산
total_cnt = len(df)
ped_ratio = (df["신호등구분"] == 2).mean() * 100
install_dist = df["신호기설치방식"].value_counts()

# 5. 상단 메트릭 & 차트
col1, col2, col3 = st.columns(3)
col1.metric("전체 신호등 수", f"{total_cnt}")
col2.metric("보행자용 비율", f"{ped_ratio:.1f}%")
col3.metric(f"'{region or '전체'}' 신호등 수", f"{total_cnt}")

st.subheader("🛠️ 설치방식별 분포")
st.bar_chart(install_dist)

# 6. 지도 캐싱 & 로드 설정
CACHE_PATH = "cached_signals_map.html"

@st.cache_resource
def create_and_cache_map(path: str, df_map: pd.DataFrame):
    center = utils.get_densest_coordinates()
    m = folium.Map(location=center, zoom_start=14, tiles="CartoDB positron")
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in df_map.iterrows():
        category = utils.get_signal_category(row["신호등구분"])
        color = utils.get_signal_color(category)
        popup_html = (
            f"<b>주소:</b> {row['소재지도로명주소']}<br>"
            f"<b>신호등 구분:</b> {category}<br>"
            f"<b>설치방식:</b> {row['신호기설치방식']}"
        )
        folium.Marker(
            location=[row["위도"], row["경도"]],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(marker_cluster)
    m.save(path)
    return path

# 최초 실행 시만 맵 생성
if not os.path.exists(CACHE_PATH):
    create_and_cache_map(CACHE_PATH, df)

from sklearn.cluster import DBSCAN
coords = df[['위도','경도']].values
db = DBSCAN(eps=0.001, min_samples=5).fit(coords)  # eps 조정 필요
df['cluster'] = db.labels_
st.subheader("🔎 설치 클러스터 개수")
st.write(df['cluster'].nunique() - (1 if -1 in df['cluster'] else 0))

by_road = df['도로형태'].value_counts()
st.subheader("🛣️ 도로형태별 신호등 분포")
st.bar_chart(by_road)

# 7. 하단에 HTML 맵 로드
st.subheader("📍 신호등 위치 지도 (캐시된 HTML)")
with open(CACHE_PATH, 'r', encoding='utf-8') as f:
    html_data = f.read()
components.html(html_data, height=600)
