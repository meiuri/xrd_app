import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pickle
import os
from PIL import Image

# ==========================================
# ⚙️ アプリケーション設定
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, "xrd_icon.jpg")

if os.path.exists(icon_path):
    icon_img = Image.open(icon_path)
else:
    icon_img = "🕊️" 

st.set_page_config(
    page_title="XRD Plotter Pro",
    page_icon=icon_img,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 定数・初期設定 ---
WAVELENGTH = 1.789  # Å (Co Kα)

# --- 🎨 カスタムCSS (クリーンなライトモード) ---
st.markdown("""
<style>
    .stApp {
        background-color: #FFFFFF;
        color: #0F1419;
    }
    .st-emotion-cache-1wrcr25 {
        background-color: #F7F9F9;
    }
    div.stButton > button[kind="primary"] {
        background-color: #1D9BF0;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 10px 20px;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1A8CD8;
    }
    .collection-card {
        background-color: #F7F9F9;
        border: 1px solid #EFF3F4;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 8px;
        color: #0F1419;
    }
    /* 不要なマージンを削ってスッキリさせる */
    .stMarkdown {
        margin-bottom: -10px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State 初期化 ---
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = {}
if "file_settings" not in st.session_state:
    st.session_state.file_settings = pd.DataFrame(columns=["File", "👁️ Show", "⭐ Highlight"])
if "collections" not in st.session_state:
    st.session_state.collections = {}

# --- 関数群 ---
def read_rigaku_ras(file):
    angles, intensity = [], []
    in_data = False
    lines = file.getvalue().decode("utf-8", errors="ignore").splitlines()
    for line in lines:
        if "*RAS_DATA_START" in line: in_data = True
        elif "*RAS_DATA_END" in line: break
        elif in_data:
            try:
                vals = line.split()
                angles.append(float(vals[0]))
                intensity.append(float(vals[1]))
            except: continue
    return np.array(angles), np.array(intensity)

# ----------------------------------------------------
# 🌟 3カラムレイアウト
# ----------------------------------------------------
left_col, main_col, right_col = st.columns([2.5, 6, 3.0], gap="large")

# ==========================================
# 🏠 左カラム：データ入力 ＆ アカウント管理
# ==========================================
with left_col:
    if os.path.exists(icon_path):
        st.image(icon_path, width=60)
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True) # 余白

    # 文字の重複をなくし、ラベルを隠してスッキリさせる
    st.markdown("**📂 データの追加**")
    new_files = st.file_uploader("ファイルアップロード", label_visibility="collapsed", type=["ras"], accept_multiple_files=True)
    
    if new_files:
        new_entries = []
        for file in new_files:
            if file.name not in st.session_state.uploaded_data:
                x, y = read_rigaku_ras(file)
                st.session_state.uploaded_data[file.name] = {"x": x, "y": y}
                new_entries.append({"File": file.name, "👁️ Show": True, "⭐ Highlight": False})
        
        if new_entries:
            st.session_state.file_settings = pd.concat(
                [st.session_state.file_settings, pd.DataFrame(new_entries)], ignore_index=True
            )
            st.rerun()

    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)

    st.markdown("**👥 データリスト**")
    if not st.session_state.file_settings.empty:
        edited_df = st.data_editor(
            st.session_state.file_settings,
            hide_index=True,
            use_container_width=True,
            column_config={
                "File": st.column_config.TextColumn("ファイル名", disabled=True),
                "👁️ Show": st.column_config.CheckboxColumn("表示"),
                "⭐ Highlight": st.column_config.CheckboxColumn("強調")
            }
        )
        st.session_state.file_settings = edited_df
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ 全データ削除", use_container_width=True):
            st.session_state.uploaded_data = {}
            st.session_state.file_settings = pd.DataFrame(columns=["File", "👁️ Show", "⭐ Highlight"])
            st.rerun()
    else:
        st.caption("読み込まれたデータはありません")

# ==========================================
# 📱 中央カラム：プロット ＆ 編集
# ==========================================
with main_col:
    st.markdown("### 📊 XRD プロット")
    
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 2])
    with col1: 
        use_log = st.checkbox("Log Scale", value=True)
    with col2: 
        x_min = st.number_input("X軸 Min", value=35.0, step=1.0, format="%.1f")
    with col3: 
        x_max = st.number_input("X軸 Max", value=45.0, step=1.0, format="%.1f")
    with col4:
        y_min = st.number_input("表示下限 (Y軸)", min_value=0.1, value=1.0, step=1.0, format="%.1f")

    x_range = [x_min, x_max]
    offset_val = st.number_input("🧵 Y軸ずらし量 (比較用)", min_value=0.0, value=0.0, step=0.1, format="%.2f")

    # --- プロット描画 ---
    with st.container(border=True):
        fig = go.Figure()
        
        academic_colors = ['#000000', '#D62728', '#1F77B4', '#2CA02C', '#FF7F0E', '#9467BD']
        active_files = st.session_state.file_settings[st.session_state.file_settings["👁️ Show"] == True]
        
        global_max_y = 1.0

        for i, row in active_files.reset_index().iterrows():
            fname = row["File"]
            highlight = row["⭐ Highlight"]
            data = st.session_state.uploaded_data[fname]
            x_plot, y_plot = data["x"], data["y"]

            if use_log:
                y_display = y_plot * (10 ** (i * offset_val * 2))
            else:
                y_display = y_plot + (i * offset_val * (max(y_plot) * 0.2))

            range_mask = (x_plot >= x_range[0]) & (x_plot <= x_range[1])
            if len(y_display[range_mask]) > 0:
                global_max_y = max(global_max_y, np.max(y_display[range_mask]))

            line_color = academic_colors[i % len(academic_colors)] if not highlight else "#FF0000"
            line_width = 3.0 if highlight else 1.5

            fig.add_trace(go.Scatter(x=x_plot, y=y_display, mode='lines', name=fname, line=dict(color=line_color, width=line_width)))

        if use_log:
            safe_y_min = max(y_min, 1e-5)
            y_display_range = [np.log10(safe_y_min), np.log10(global_max_y * 1.5)]
        else:
            y_display_range = [y_min, global_max_y * 1.1]

        fig.update_layout(
            xaxis=dict(title="2θ (deg)", range=[x_range[0], x_range[1]], showgrid=False, linecolor='black', mirror=True, ticks='inside'),
            yaxis=dict(
                title="Log Intensity (a.u.)" if use_log else "Intensity (a.u.)",
                type="log" if use_log else "linear",
                range=y_display_range, showgrid=False, linecolor='black', mirror=True, ticks='inside', showticklabels=False
            ),
            height=500, margin=dict(l=20, r=20, t=30, b=20),
            plot_bgcolor="white", paper_bgcolor="white", font=dict(color="black", family="Arial"),
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99, font=dict(color="black"))
        )
        
        fig.update_xaxes(title_font=dict(size=20, color='black'), tickfont=dict(size=16, color='black'))
        fig.update_yaxes(title_font=dict(size=20, color='black'))

        post_text = st.text_area("📝 メモ (グラフ内に印字されます)", max_chars=140, placeholder="測定条件や考察をメモ...", label_visibility="collapsed")
        if post_text:
            fig.update_layout(title=dict(text=f"{post_text}", font=dict(size=16, color="black", family="Arial")))

        clean_config = {
            'displayModeBar': True,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines'],
            'displaylogo': False,
            'toImageButtonOptions': {'format': 'png', 'filename': 'xrd_plot_highres', 'height': 600, 'width': 800, 'scale': 3}
        }
        st.plotly_chart(fig, use_container_width=True, config=clean_config)

# ==========================================
# 🔍 右カラム：ツール ＆ 保存の完全統合
# ==========================================
with right_col:
    
    # --- 1. 右上の「保存済み」ボタン (ポップオーバーで展開) ---
    with st.popover("📚 保存済みギャラリーを開く", use_container_width=True):
        st.markdown("#### 🔖 コレクション一覧")
        if st.session_state.collections:
            for name in st.session_state.collections.keys():
                st.markdown(f'<div class="collection-card"><b>{name}</b></div>', unsafe_allow_html=True)
                if st.button(f"🔄 復元する", key=f"load_{name}", use_container_width=True):
                    st.session_state.uploaded_data = st.session_state.collections[name]["uploaded_data"]
                    st.session_state.file_settings = st.session_state.collections[name]["file_settings"]
                    st.rerun()
            
            st.divider()
            st.markdown("#### 📥 ファイル入出力")
            export_data = pickle.dumps(st.session_state.collections)
            st.download_button("📁 PCへバックアップ (.pkl)", data=export_data, file_name="xrd_collections.pkl", mime="application/octet-stream", use_container_width=True)
        else:
            st.info("保存されたデータはありません。")

        st.divider()
        uploaded_pkl = st.file_uploader("📂 バックアップを読む", type=["pkl"], label_visibility="collapsed")
        if uploaded_pkl:
            if st.button("バックアップを復元"):
                st.session_state.collections = pickle.load(uploaded_pkl)
                st.success("復元完了！上のリストから選択してください。")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True) # 少し余白をあける

    # --- 2. 解析ツール ＆ その直下での保存機能 ---
    st.markdown("### 🔍 解析ツール")
    
    # ▼ ここから一つの「枠」にまとめる ▼
    with st.container(border=True):
        st.caption(f"※ 入射X線波長 $\\lambda = {WAVELENGTH}$ Å")
        
        if not st.session_state.file_settings.empty:
            target_file = st.selectbox("対象ファイル", options=st.session_state.file_settings["File"].tolist())
            
            s_col1, s_col2 = st.columns(2)
            with s_col1: search_min = st.number_input("探索 Min", value=x_range[0], format="%.2f")
            with s_col2: search_max = st.number_input("探索 Max", value=x_range[1], format="%.2f")
            
            c_sys = st.selectbox("結晶系", ["Cubic (立方晶)", "Hexagonal/Trigonal (六・三方晶)", "Tetragonal (正方晶)"])
            st.markdown("**ミラー指数 (h k l)**")
            col_h, col_k, col_l = st.columns(3)
            with col_h: h_val = st.number_input("h", value=0, step=1)
            with col_k: k_val = st.number_input("k", value=0, step=1)
            with col_l: l_val = st.number_input("l", value=6, step=1)
            
            known_param, known_val = None, None
            if c_sys != "Cubic (立方晶)" and not (h_val == 0 and k_val == 0) and l_val != 0:
                st.caption("💡 非対称反射のため、片方の格子定数が必要です。")
                known_param = st.radio("既知のパラメータ", ["a を入力", "c を入力"], label_visibility="collapsed")
                known_val = st.number_input(f"既知の {known_param[0]} (Å)", value=5.000, format="%.4f")

            if st.button("🚀 ピーク特定＆計算", type="primary", use_container_width=True):
                data = st.session_state.uploaded_data[target_file]
                x_raw, y_raw = data["x"], data["y"]
                mask = (x_raw >= search_min) & (x_raw <= search_max)
                
                if len(x_raw[mask]) > 0:
                    max_idx = np.argmax(y_raw[mask])
                    found_peak = x_raw[mask][max_idx]
                    
                    theta_rad = np.radians(found_peak / 2)
                    d_spacing = WAVELENGTH / (2 * np.sin(theta_rad))
                    
                    st.success(f"📌 **ピーク位置:** {found_peak:.4f}°  |  $d$ : **{d_spacing:.4f} Å**")
                    
                    if h_val == 0 and k_val == 0 and l_val == 0:
                        st.warning("ミラー指数が(000)のため格子定数は計算できません。")
                    else:
                        try:
                            if c_sys == "Cubic (立方晶)":
                                a_val = d_spacing * np.sqrt(h_val**2 + k_val**2 + l_val**2)
                                st.info(f"**格子定数 $a$ = {a_val:.4f} Å**")
                            elif c_sys == "Hexagonal/Trigonal (六・三方晶)":
                                if h_val == 0 and k_val == 0:
                                    st.info(f"**格子定数 $c$ = {d_spacing * l_val:.4f} Å**")
                                elif l_val == 0:
                                    st.info(f"**格子定数 $a$ = {d_spacing * np.sqrt(4 * (h_val**2 + h_val*k_val + k_val**2) / 3):.4f} Å**")
                                else:
                                    if known_param.startswith("a"):
                                        term1 = (4 * (h_val**2 + h_val*k_val + k_val**2)) / (3 * known_val**2)
                                        term2 = (1 / d_spacing**2) - term1
                                        st.info(f"**計算結果 $c$ = {np.sqrt(l_val**2 / term2):.4f} Å**")
                                    else:
                                        term1 = l_val**2 / known_val**2
                                        term2 = (1 / d_spacing**2) - term1
                                        st.info(f"**計算結果 $a$ = {np.sqrt((4 * (h_val**2 + h_val*k_val + k_val**2)) / (3 * term2)):.4f} Å**")
                            elif c_sys == "Tetragonal (正方晶)":
                                if h_val == 0 and k_val == 0:
                                    st.info(f"**格子定数 $c$ = {d_spacing * l_val:.4f} Å**")
                                elif l_val == 0:
                                    st.info(f"**格子定数 $a$ = {d_spacing * np.sqrt(h_val**2 + k_val**2):.4f} Å**")
                                else:
                                    if known_param.startswith("a"):
                                        term1 = (h_val**2 + k_val**2) / (known_val**2)
                                        term2 = (1 / d_spacing**2) - term1
                                        st.info(f"**計算結果 $c$ = {np.sqrt(l_val**2 / term2):.4f} Å**")
                                    else:
                                        term1 = l_val**2 / known_val**2
                                        term2 = (1 / d_spacing**2) - term1
                                        st.info(f"**計算結果 $a$ = {np.sqrt((h_val**2 + k_val**2) / term2):.4f} Å**")
                        except Exception:
                            st.error("エラー: パラメータが不適切です。")
                else:
                    st.warning("範囲内にデータがありません。")

            st.divider()

            # --- 解析ツールと同じ枠内に配置した「保存」 ---
            st.markdown("**🔖 この状態を保存**")
            col_name = st.text_input("保存名", key="save_name", label_visibility="collapsed", placeholder="例: CoFe2O4_比較用")
            
            if st.button("➕ コレクションに追加", use_container_width=True):
                if col_name:
                    st.session_state.collections[col_name] = {
                        "uploaded_data": st.session_state.uploaded_data,
                        "file_settings": st.session_state.file_settings
                    }
                    st.success(f"右上のギャラリーに保存しました！")
                else:
                    st.error("名前を入力してください。")
        else:
            st.info("👈 左からデータを読み込んでください。")