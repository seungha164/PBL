import pandas as pd
import numpy as np


DF_BLINKER = pd.read_csv("files2/refined/blinker.csv")
DF_ACCIDENT = pd.read_csv("files2/refined/accident.csv")


# def compute_map_center():
#     #  위도와 경도의 평균을 계산해서 중심으로 설정
#     center_lat = DF_BLINKER['위도'].mean()
#     center_lng = DF_BLINKER['경도'].mean()
#     return 

from scipy.stats import gaussian_kde

def get_densest_coordinates():
    """
    특정 시군명 내에서 위도/경도가 가장 밀집된 좌표 반환
    """
    df = DF_ACCIDENT
    coords = np.vstack([df['위도'], df['경도']])
    kde = gaussian_kde(coords)
    
    # 밀도 추정할 좌표들
    density = kde(coords)
    max_idx = np.argmax(density)

    densest_lat = df.iloc[max_idx]['위도']
    densest_lng = df.iloc[max_idx]['경도']
    
    return densest_lat, densest_lng