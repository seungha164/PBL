import pandas as pd
import folium
import ast  # 문자열 → 리스트 파싱용

# 1. CSV 불러오기
df = pd.read_csv("/home/nute11a/workspace/PBL/SUWON/code/data/origin/suwon_CCTV.csv")  # 실제 파일 경로로 교체

m = folium.Map(location=[37.26, 126.93], zoom_start=12)

# 3. 폴리곤 반복 추가
for idx, row in df.iterrows():
    try:
        # 좌표 리스트 변환
        raw_coords = ast.literal_eval(row["PXL_CRDNT"])  # [[[lon, lat], ...]]
        # folium은 (lat, lon) 순서를 요구하므로 순서 바꾸기
        coords = [[lat, lon] for lon, lat in raw_coords[0]]
        # polygon에 값 vis
        PLAC_CNT = row["PLAC_CNT"]
        folium.Polygon(
            
            locations=coords,
            color='white' if row['PLAC_CNT'] == 0 else 'red',
            fill=True,
            fill_color='blue',
            fill_opacity=0 if row['PLAC_CNT'] == 0 else 0.2,
            tooltip=row["PLAC_CNT"]
        ).add_to(m)

    except Exception as e:
        print(f"Error at row {idx}: {e}")

# 4. 저장
m.save("suwon_map.html")
m
