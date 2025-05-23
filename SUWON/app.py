from flask import Flask, render_template, render_template, request
import folium
import os
import pandas as pd
from folium.plugins import MarkerCluster, FastMarkerCluster
import json
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely import wkt
from shapely.geometry import Polygon


app = Flask(__name__)

grid = gpd.read_file('/home/nute11a/workspace/PBL/SUWON/code/data/preprocessed/grid_with_score.geojson', engine="pyogrio")
# 3) (Choropleth 사용) index 필드를 데이터와 매칭하기 위해 reset_index
# grid = grid.reset_index().rename(columns={"index":"grid_id"})
# 2) 랜덤 score 생성 (0~1 사이)
# np.random.seed(42)  # 재현 가능하도록 시드 고정
# grid["score"] = np.random.rand(len(grid))

# 가로등 데이터 로드
streetlights_df = pd.read_csv(os.path.join(app.static_folder, 'data', 'streetlights_data3.csv'))

# 2) 사전 계산된 통계 JSON 로드
with open(os.path.join(app.static_folder,'data','streetlights_stats.json'), encoding='utf-8') as f:
    GLOBAL_STATS = json.load(f)

# 설치연도 최소/최대값 계산 (슬라이더 범위 동적 설정)
year_min = int(streetlights_df['install_year'].min())
year_max = int(streetlights_df['install_year'].max())

@app.route('/')
def index():
    # 필터 전 통계는 GLOBAL_STATS 사용
    stats = GLOBAL_STATS
    
    # 기본 지도 렌더링 (필터 없이 전체 데이터)
    m = folium.Map(location=[37.2983, 127.0355], zoom_start=15)
    locations = [
        [
            row['lat'], 
            row['lon'],
            row['status'],
            f"가로등 {row['id']}: {row['status']}<br>설치연도: {row['install_year']}"
        ]
        for _, row in streetlights_df.iterrows()
    ]
    icon_callback = """
    function(row) {
        var lat = row[0], lon = row[1], status = row[2], popup = row[3];
        var color = (status === '정상') ? 'green' : 'red';
        var marker = L.circleMarker([lat, lon], {
            radius: 6,
            color: color,
            fillColor: color,
            fillOpacity: 0.9
        });
        marker.bindPopup(popup);
        return marker;
    }
    """

    # 4) FastMarkerCluster 적용
    FastMarkerCluster(
        data=locations,
        callback=icon_callback
    ).add_to(m)
    # marker_cluster = MarkerCluster().add_to(m)

    # for _, row in streetlights_df.iterrows():
    #     color = 'green' if row['status'] == '정상' else 'red'
    #     folium.Marker(
    #         location=[row['lat'], row['lon']],
    #         popup=f"가로등 {row['id']}: {row['status']}<br>설치연도: {row['install_year']}",
    #         icon=folium.Icon(color=color)
    #     ).add_to(marker_cluster)

    # folium.GeoJson(
    #     grid.__geo_interface__,
    #     name="grid",
    #     style_function=lambda feat: {
    #         "color": "#555555",
    #         "weight": 1,
    #         "fillOpacity": 0
    #     }
    # ).add_to(m)
    # 4) Choropleth 레이어 추가
    folium.Choropleth(
        geo_data=grid.__geo_interface__,
        name="safety_score",
        data=grid,
        columns=["grid_id", "score"],
        key_on="feature.properties.grid_id",
        fill_color="RdYlGn",      # 색상맵: Yellow→Orange→Red
        fill_opacity=0.4,
        line_opacity=0.2,
        legend_name="Grid Safety Score"
    ).add_to(m)
    folium.GeoJson(
        grid.__geo_interface__,
        name="score-tooltip",
        style_function=lambda feat: {"opacity": 0, "fillOpacity": 0},
        tooltip=folium.features.GeoJsonTooltip(
            fields=["grid_id", "score"],
            aliases=["Grid ID", "Score"],
            localize=True
        )
    ).add_to(m)
    
    folium.LayerControl().add_to(m)

    map_html = m._repr_html_()
    return render_template('index.html', 
                        map_html=map_html, 
                        total_count=len(streetlights_df), 
                        streetlights_df=streetlights_df, 
                        filtered_count=len(streetlights_df),
                        status_filter='all', 
                        year_min_filter=year_min, 
                        year_max_filter=year_max,
                        year_min=year_min, 
                        year_max=year_max,
                        # 통계 전달
                        total=stats['total'],
                        normal=stats['normal'],
                        broken=stats['broken'],
                        year_counts=stats['year_counts'],
                        fault_rate=stats['fault_rate'],
                    )

    
@app.route('/stats')
def stats():
    stats = GLOBAL_STATS
    return render_template('stats.html',
        total=stats['total'],
        normal=stats['normal'],
        broken=stats['broken'],
        year_counts=stats['year_counts'],
        fault_rate=stats['fault_rate'],
        dong_stats = stats['dong_state'],
    )

@app.route('/filter', methods=['POST'])
def filter():
    # 필터 값 가져오기
    status_filter = request.form.get('status', 'all')
    year_min_filter = int(request.form.get('year_min', year_min))
    year_max_filter = int(request.form.get('year_max', year_max))

    # 데이터 필터링
    df = streetlights_df.copy()
    if status_filter != 'all':
        df = df[df['status'] == status_filter]
    df = df[(df['install_year'].between(year_min_filter, year_max_filter))]

    # 필터링된 데이터로 지도 생성
    m = folium.Map(location=[37.2983, 127.0355], zoom_start=15)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        color = 'green' if row['status'] == '정상' else 'red'
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=f"가로등 {row['id']}: {row['status']}<br>{row['address']}<br>설치연도: {row['install_year']}",
            icon=folium.Icon(color=color)
        ).add_to(marker_cluster)

    map_html = m._repr_html_()
    return render_template('index.html', map_html=map_html, total_count=len(streetlights_df), 
                          streetlights_df=df, filtered_count=len(df),
                          status_filter=status_filter, year_min_filter=year_min_filter, 
                          year_max_filter=year_max_filter, year_min=year_min, year_max=year_max)

if __name__ == '__main__':
    app.run(debug=True)