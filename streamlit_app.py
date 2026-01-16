import streamlit as st
import requests
import pandas as pd
import numpy as np
import pydeck as pdk

# --- ページ設定 ---
st.set_page_config(page_title="九州気温 3D Map", layout="wide")
st.title("九州主要都市の気温 3Dカラムマップ（時間変化対応）")

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

# --- 気温 → 色変換関数 ---
def temp_to_color(temp):
    """低温→青、中間→緑、高温→赤 のグラデーション"""
    t = np.clip((temp + 5) / 40, 0, 1)  # -5〜35℃を0〜1に正規化
    r = int(255 * t)
    g = int(255 * (1 - abs(t - 0.5) * 2))
    b = int(255 * (1 - t))
    return [r, g, b, 180]

# --- データ取得関数（時系列対応） ---
@st.cache_data(ttl=600)
def fetch_weather_data():
    weather_info = []
    BASE_URL = 'https://api.open-meteo.com/v1/forecast'
    
    for city, coords in kyushu_capitals.items():
        params = {
            'latitude':  coords['lat'],
            'longitude': coords['lon'],
            'hourly': 'temperature_2m',
            'timezone': 'Asia/Tokyo',
            'past_days': 1
        }
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            times = data['hourly']['time']
            temps = data['hourly']['temperature_2m']

            for t, temp in zip(times, temps):
                weather_info.append({
                    'City': city,
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'time': pd.to_datetime(t),
                    'Temperature': temp
                })

        except Exception as e:
            st.error(f"Error fetching {city}: {e}")
            
    return pd.DataFrame(weather_info)

# データの取得
with st.spinner('最新の気温データを取得中...'):
    df = fetch_weather_data()

# elevation と color を計算
df['elevation'] = df['Temperature'] * 3000
df['color'] = df['Temperature'].apply(temp_to_color)

# --- UI：時刻スライダー ---
st.subheader("表示する時刻を選択")

df['time'] = pd.to_datetime(df['time']).dt.to_pydatetime()

selected_time = st.slider(
    "時刻",
    min_value=df['time'].min(),
    max_value=df['time'].max(),
    value=df['time'].min(),
    format="YYYY-MM-DD HH:mm"
)

# 選択された時刻のデータだけ抽出
df_selected = df[df['time'] == selected_time]

# --- メインレイアウト ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("取得したデータ")
    st.dataframe(df_selected[['City', 'Temperature']], use_container_width=True)
    
    if st.button('データを更新'):
        st.cache_data.clear()
        st.rerun()

with col2:
    st.subheader("3D カラムマップ（時間変化対応）")

    view_state = pdk.ViewState(
        latitude=32.7,
        longitude=131.0,
        zoom=6.2,
        pitch=45,
        bearing=0
    )

    layer = pdk.Layer(
        "ColumnLayer",
        data=df_selected,               # ★ 時刻で絞ったデータを使用
        get_position='[lon, lat]',
        get_elevation='elevation',
        radius=12000,
        get_fill_color='color',         # ★ 気温に応じた色
        pickable=True,
        auto_highlight=True,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{City}</b><br>気温: {Temperature}°C<br>時刻: {time}",
            "style": {"color": "white"}
        }
    ))
    
