import streamlit as st
import folium
from streamlit_folium import st_folium
import utils

# 2. Streamlit UI 설정
st.set_page_config(page_title="신호등 지도 시각화", layout="centered")
st.title("🚦 신호등 위치 시각화")
st.markdown("보행자용과 차량용 신호등을 색상과 팝업 정보로 구분하여 지도에 표시합니다.")


# # 지도 중심 좌표 (수원역 기준, 위도/경도)
center_lat, center_lng = utils.get_densest_coordinates()

# 3. 지도 생성
m = folium.Map(location=[center_lat, center_lng], zoom_start=13)

# # 지도 생성
# m = folium.Map(location=[center_lat, center_lng], zoom_start=19, tiles='CartoDB positron')  # 깔끔한 배경

# # 반경 1000m (1km) 원 추가
# # folium.Circle(
# #     radius=1000,
# #     location=[center_lat, center_lng],
# #     popup="1km Radius",
# #     color="blue",
# #     fill=True,
# #     fill_opacity=0.1
# # ).add_to(m)

# # 지도 출력 (Jupyter 환경에서는 자동 출력됨)
# m.save('map.html')  # 또는 m._repr_html_() 사용
st_data = st_folium(m, width=700, height=500)
# print("지도가 생성되었습니다! 'map.html' 파일을 열어보세요.")
