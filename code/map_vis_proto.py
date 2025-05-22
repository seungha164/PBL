import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from scipy.spatial import cKDTree
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

# 0. 페이지 설정
st.set_page_config("🚶‍♀️🚦 강남구 사고·보행등 대시보드", layout="wide")

# 1. 데이터 로드 & 필터링
csv_root = "../files2/final"
# datetime 컬럼을 바로 파싱
df_acc = pd.read_csv(
    f"{csv_root}/seoul_accidents.csv",
    parse_dates=["datetime"],
    dtype={"day_night": str, "day_of_week": str}
)
df_light = pd.read_csv(f"{csv_root}/seoul_traffic_lights.csv")

# 강남구 데이터만, 위경도 결측치 제거
df_acc   = df_acc[df_acc["district"] == "강남구"].dropna(subset=["lat","lon"])
df_light = df_light[df_light["district"] == "강남구"].dropna(subset=["lat","lon"])

# day_night 컬럼 "주간"/"야간" → "주"/"야"
df_acc["day_night"] = df_acc["day_night"].map({"주간":"주", "야간":"야"})

# 2. 사이드바: 시간대별 필터링
hour_range = st.sidebar.slider(
    "⏱️ 시간대별 필터링",
    0, 23, (0, 23),
    help="대시보드에 표시할 사고 발생 시간대를 선택하세요."
)
mask_time   = df_acc["datetime"].dt.hour.between(*hour_range)
df_acc_filt = df_acc[mask_time]

# 3. 사고→보행등 거리 계산
tree = cKDTree(df_light[["lat","lon"]].values)
indices = tree.query(df_acc_filt[["lat","lon"]].values)[1]
dists = np.array([
    geodesic(
        (row.lat, row.lon),
        (df_light.iloc[idx].lat, df_light.iloc[idx].lon)
    ).meters
    for row, idx in zip(df_acc_filt.itertuples(), indices)
])

# 4. 기본 메트릭
accidents_count = len(df_acc_filt)
lights_count    = len(df_light)
avg_dist        = dists.mean()
median_dist     = np.median(dists)

# 5. 그리드별 상관계수 & 핫스팟
gs = 0.005
def assign_grid(df):
    df = df.copy()
    df["gx"] = (df.lat // gs) * gs
    df["gy"] = (df.lon // gs) * gs
    return df

g_acc   = assign_grid(df_acc_filt)
g_light = assign_grid(df_light)
a_cnt = g_acc.groupby(["gx","gy"]).size().rename("acc")
l_cnt = g_light.groupby(["gx","gy"]).size().rename("light")
df_grid = a_cnt.to_frame().join(l_cnt, how="outer").fillna(0)
corr    = df_grid["acc"].corr(df_grid["light"])
df_grid["score"] = df_grid["acc"] - df_grid["light"]
hotspots = df_grid.nlargest(5, "score").reset_index()

# 6. 핵심 통계 패널
st.title(f"📊 핵심 통계 (강남구 · {hour_range[0]}시–{hour_range[1]}시)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("사고 건수",     accidents_count)
c2.metric("보행등 수",     lights_count)
c3.metric("평균 거리 (m)", f"{avg_dist:.1f}")
c4.metric("중앙값 거리 (m)", f"{median_dist:.1f}")

c5, c6, c7, c8 = st.columns(4)
# CDF로 50%·80% 커버리지 계산
hist, edges = np.histogram(dists, bins=[0,50,100,200,500,1000])
hist, edges = np.histogram(dists, bins=100, range=(0, edges[-1]))
cdf = np.cumsum(hist) / hist.sum()
cover50 = float(np.interp(0.5, cdf, edges[1:]))
cover80 = float(np.interp(0.8, cdf, edges[1:]))
c5.metric("50% 커버 반경 (m)", f"{cover50:.0f}")
c6.metric("80% 커버 반경 (m)", f"{cover80:.0f}")
c7.metric("격자 상관계수", f"{corr:.2f}")
c8.metric("핫스팟 격자 수", int((df_grid.score > 0).sum()))



import overpy

api = overpy.Overpass()
# 강남구 대략 바운딩 박스(위도,경도)를 직접 지정하세요
bbox = (37.49, 127.02, 37.52, 127.06)
query = f"""
node
  [amenity=bar]
  ({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
out;
"""
result = api.query(query)

# DataFrame 으로 변환
bars = []
for node in result.nodes:
    bars.append({
        "lat": float(node.lat),
        "lon": float(node.lon),
        "name": node.tags.get("name","주점")
    })
df_bars = pd.DataFrame(bars)


# 7. 지도 시각화
center = [df_acc_filt.lat.mean(), df_acc_filt.lon.mean()]
m = folium.Map(center, zoom_start=14, tiles="OpenStreetMap")#tiles="CartoDB positron")

# 주점
bar_cluster = MarkerCluster(name="🍺 주점(Bar)").add_to(m)
for _, r in df_bars.iterrows():
    folium.Marker(
        [r.lat, r.lon],
        icon=folium.Icon(color="darkred", icon="glass", prefix="fa"),
        tooltip=r.name
    ).add_to(bar_cluster)


HeatMap(df_acc_filt[["lat","lon"]].values.tolist(),
        radius=8, blur=12, name="사고 HeatMap").add_to(m)
mc = MarkerCluster(name="보행등").add_to(m)
for _, r in df_light.iterrows():
    folium.CircleMarker(
        [r.lat, r.lon],
        radius=3, color="blue", fill=True, fill_opacity=0.6
    ).add_to(mc)
hs = MarkerCluster(name="핫스팟").add_to(m)
for _, row in hotspots.iterrows():
    lat0, lon0 = row.gx + gs/2, row.gy + gs/2
    folium.Marker(
        [lat0, lon0],
        icon=folium.Icon(color="red", icon="warning"),
        popup=f"사고={int(row.acc)}, 등={int(row.light)}, 점수={int(row.score)}"
    ).add_to(hs)
folium.LayerControl().add_to(m)
st.subheader("📍 사고·보행등 분포 지도")
st.caption("⏳ 사이드바에서 시간대를 조정해 필터링할 수 있습니다.")
st_folium(m, width=900, height=600)

# 8. 거리 분포 히스토그램
st.subheader("📊 사고→보행등 거리 분포")
fig, ax = plt.subplots()
ax.hist(dists, bins=[0,50,100,200,500,1000], edgecolor="k")
ax.set_xlabel("거리 (m)"); ax.set_ylabel("사고 건수")
st.pyplot(fig)

# 9. 시간·유형 분석 차트
st.markdown("---")
# 1) 사고→최근접 주점 거리 계산
bar_tree = cKDTree(df_bars[["lat","lon"]].values)
d_bar = []
for lat,lon in zip(df_acc.lat, df_acc.lon):
    _, idx = bar_tree.query((lat, lon))
    d_bar.append(geodesic((lat,lon),(df_bars.iloc[idx].lat,df_bars.iloc[idx].lon)).meters)
d_bar = np.array(d_bar)

# 2) bar_dist 히스토그램
# 1) 사고→주점 거리 배열 d_bar 가 이미 계산되어 있다고 가정
#    bins 는 원하는 구간으로 설정
bins = [0, 100, 200, 500, 1000]
hist, edges = np.histogram(d_bar, bins=bins)

# 2) 구간 라벨 생성
labels = [f"{int(edges[i])}–{int(edges[i+1])}m" for i in range(len(edges)-1)]

# 3) DataFrame으로 정리
df_hist = pd.DataFrame({
    "사고 건수": hist
}, index=labels)

# 4) st.bar_chart 로 시각화
st.subheader("🍺 사고→최근접 주점 거리 분포")
st.bar_chart(df_hist)

st.subheader("⏰ 시간·유형 분석 차트")
# 9-1) 시간대별 사고 분포
hour_counts = df_acc_filt["datetime"].dt.hour.value_counts().sort_index()
st.write("### 시간대별 사고 분포")
st.bar_chart(hour_counts)
# 9-6) AI 해설 & 개선 추천
st.markdown(
    "### 🤖 AI의 답변\n"
    "- **새벽(0~6시)에 사고가 집중됩니다.** : 야간·새벽에는 시야가 좁고, 음주·과속 비율이 올라가 사고 위험이 높아집니다.\n"
    "- **출퇴근(7~9시) 사고는 상대적으로 적습니다.** : 교통량이 많아 속도가 낮아지고, 운전자·보행자 모두 경각심을 갖는 시기이기 때문으로 보입니다.\n"
    "- **저녁(22~23시) 사고가 다시 증가합니다.** : 야간 어둠, 주말 저녁 술자리 귀가, 조명·신호체계 미흡 등이 원인일 수 있습니다.\n\n"
    "🔧 **시사점 & 개선 추천**\n"
    "- **야간·새벽 조명 강화**: 가로등·가로수 조명, 반사판 확대 설치\n"
    "- **음주·과속 단속 집중**: 0~6시, 22~24시 사이 단속 강화"
)

# 9-2) 요일별 사고 분포
order = ["월","화","수","목","금","토","일"]
wd_counts = df_acc_filt["day_of_week"].value_counts().reindex(order).fillna(0)
# 순서 -> 월화수목금토일
wd_counts.index = ["월","화","수","목","금","토","일"]
wd_counts = wd_counts.astype(int)
st.write("### 요일별 사고 분포")
st.bar_chart(wd_counts)
st.markdown(
    "### 🤖 AI의 해석\n"
    "- **수요일(약 38건)**\n"
    "  한 주 중 가장 사고가 많이 발생하는 날로, 출·퇴근 교통량 및 업무 피크 시간이 가장 극심한 요일입니다.\n"
    "- **월요일(약 36건)**  \n"
    "주초 ‘업무 모드’ 전환 시점에 긴장도 저하와 교통량 급증이 겹쳐 사고가 잦아집니다.\n"
    "- **목요일·일요일(각 30~31건)**  \n"
    "평일 후반과 주말 전 ‘활동 전환기’로, 업무·여가 이동이 혼재되어 중간 수준 사고가 발생합니다.\n"
    "- **화·토요일(각 27건)** \n "
    "화요일은 업무 리듬 안정기, 토요일은 주말 여가 모드로 비교적 사고가 적은 편입니다.\n"
    "- **금요일(약 18건)**  \n"
    "한 주 마무리 분위기 속 경각심이 높아지거나, 퇴근 후 활동 패턴 변화로 사고 건수가 현저히 줄어듭니다.\n\n"

    "### 🔧 **시사점 & 제언**  \n"
    "- **중반 주 집중 단속**: 수·월요일 출퇴근 시간대에 교통단속을 강화하세요.  \n"
    "- **금요일 안전 캠페인**: 사고가 적은 금요일에 ‘연휴 대비·야간 안전’ 메시지를 적극 홍보합니다.  \n"
    "- **주말 환경 개선**: 토·일 나들이객 밀집 지역의 보행환경(노면·조명)을 점검·보강하세요.  \n"
    "- **요일별 실시간 알림**: 앱·전광판을 통해 “오늘은 수요일—출퇴근 사고 주의”와 같은 맞춤형 안내를 제공합니다.\n"
)


# 9-3) 주야별 사고 분포
dy_counts = df_acc_filt["day_night"].value_counts()
st.write("### 주야별 사고 분포")
st.bar_chart(dy_counts)

# 9-4) 사고 유형별 분포
type_counts = df_acc_filt["accident_type"].value_counts()
st.write("### 사고 유형별 분포")
st.bar_chart(type_counts)
fig2, ax2 = plt.subplots()
ax2.pie(type_counts, labels=type_counts.index, autopct="%1.1f%%", startangle=90)
ax2.axis("equal"); ax2.set_title("사고 유형별 비율")
st.pyplot(fig2)

# 9-5) 출퇴근 vs 야간 거리 CDF 비교
commute_h = [7,8,9,18,19,20]
mask_comm = df_acc_filt["datetime"].dt.hour.isin(commute_h)
mask_night= df_acc_filt["day_night"]=="야"
dist_comm = dists[mask_comm.values]
dist_nght = dists[mask_night.values]
def cdf(data, bins):
    h,e = np.histogram(data, bins=bins)
    return e[1:], np.cumsum(h)/h.sum()
bins = np.linspace(0,500,51)
x1,y1 = cdf(dist_comm, bins)
x2,y2 = cdf(dist_nght, bins)
fig3, ax3 = plt.subplots()
ax3.step(x1,y1,where="mid",label="출퇴근")
ax3.step(x2,y2,where="mid",label="야간")
ax3.set_xlabel("거리 (m)"); ax3.set_ylabel("CDF")
ax3.legend()
st.pyplot(fig3)

