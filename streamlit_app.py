import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
from mpl_toolkits.mplot3d import Axes3D

# --- ページ設定 ---
st.set_page_config(page_title="九州気温 3D Viewer", layout="wide")
st.title("九州主要都市の現在の気温 3Dプロット")

# 九州7県のデータ
kyushu_capitals = {
    'Fukuoka':    {'lat': 33.5904, 'lon': 130.4017},
    'Saga':       {'lat': 33.2494, 'lon': 130.2974},
    'Nagasaki':   {'lat': 32.7450, 'lon': 129.8739},
    'Kumamoto':   {'lat': 32.7900, 'lon': 130.7420},
    'Oita':       {'lat': 33.2381, 'lon': 131.6119},
    'Miyazaki':   {'lat': 31.9110, 'lon': 131.4240},
    'Kagoshima':  {'lat': 31.5600, 'lon': 130.5580}
}

# --- データ取得関数（キャッシュを利用） ---
@st.cache_data(ttl=600)  # 10分間データをキャッシュ
def fetch_weather_data():
    weather_info = []
    BASE_URL = 'https://api.open-meteo.com/v1/forecast'
    
    for city, coords in kyushu_capitals.items():
        params = {
            'latitude':  coords['lat'],
            'longitude': coords['lon'],
            'current': 'temperature_2m'
        }
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            weather_info.append({
                'City': city,
                'Latitude': coords['lat'],
                'Longitude': coords['lon'],
                'Temperature': data['current']['temperature_2m']
            })
        except Exception as e:
            st.error(f"Error fetching {city}: {e}")
            
    return pd.DataFrame(weather_info)

# データの取得
with st.spinner('最新の気温データを取得中...'):
    df = fetch_weather_data()

# --- メインコンテンツ ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("取得したデータ")
    st.dataframe(df, use_container_width=True)
    
    if st.button('データを更新'):
        st.cache_data.clear()
        st.rerun()

with col2:
    st.subheader("3D 可視化")
    
    # Matplotlib の描画設定
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # --- データを色付きでプロット ---
    scatter = ax.scatter(
        df['Longitude'], 
        df['Latitude'], 
        df['Temperature'], 
        c=df['Temperature'], 
        cmap='viridis', 
        s=300,        
        depthshade=True
    )

    # 垂直線の追加とラベル表示
    z_min = df['Temperature'].min() - 5
    for i in range(len(df)):
        lon, lat, tempe, city = df.iloc[i][['Longitude', 'Latitude', 'Temperature', 'City']]
        
        ax.plot([lon, lon], [lat, lat], [tempe, z_min], color='gray', linestyle='--', linewidth=1, alpha=0.6)
        ax.text(lon, lat, z_min, f'{city}\n({tempe:.1f}°C)', size=8, ha='center', va='top')

    # ラベルとタイトルの設定
    ax.set_xlabel('経度 (Longitude)')
    ax.set_ylabel('緯度 (Latitude)')
    ax.set_zlabel('気温 (°C)')
    ax.set_zlim(z_min, df['Temperature'].max() + 5)
    
    # カラーバー
    cbar = fig.colorbar(scatter, ax=ax, pad=0.1, shrink=0.5)
    cbar.set_label('気温 (°C)')

    # 視点の調整
    ax.view_init(elev=20, azim=-75)

    # Streamlitに表示
    st.pyplot(fig)

# --- 地図表示 ---
st.divider()
st.subheader("地図上での位置確認")

# 列名を明示的に指定してエラーを回避
# st.map(df, latitude='Latitude', longitude='Longitude')



import pydeck as pdk

# --- DeckGL による 3D 地図表示 ---
st.divider()
st.subheader("3D カラムマップ (気温を高さで表現)")

# 気温に基づいて柱の高さを計算（例：1度 = 2000メートル）
df['temp_height'] = df['Temperature'] * 2000 

# 地図の設定
view_state = pdk.ViewState(
    latitude=32.7,
    longitude=130.5,
    zoom=6,
    pitch=45, # 傾き
)

# 3Dカラムレイヤーの設定
layer = pdk.Layer(
    "ColumnLayer",
    data=df,
    get_position='[Longitude, Latitude]',
    get_elevation='temp_height', # 高さ
    radius=10000,                # 柱の太さ
    get_fill_color='[255, (255 - Temperature * 5), 0, 150]', # 温度が高いほど赤く
    pickable=True,
    auto_highlight=True,
)

# ツールチップ（ホバー時の表示）
tooltip = {
    "html": "<b>{City}</b><br>気温: {Temperature}°C",
    "style": {"color": "white"}
}

# 描画
st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip
))
