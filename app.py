import streamlit as st
import pandas as pd
import os
import hashlib
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
import plotly.express as px

# --- 1. IMPORT LOGIC SCRIPTS (FIXED NAMES) ---
try:
    import main as solver_engine  # Changed name to avoid confusion
    import data_validator
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Cadence Scheduler", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DIRECTORY SETUP ---
DATA_DIR = "data"
OUTPUT_DIR = "output"
ASSETS_DIR = "assets"
for d in [DATA_DIR, OUTPUT_DIR, ASSETS_DIR]:
    os.makedirs(d, exist_ok=True)

# --- LOGO ---
logo_path = os.path.join(ASSETS_DIR, "logo.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
    st.sidebar.markdown("---")

# --- CSS STYLING (DARK MODE COMPATIBLE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Headers */
    .main-header { font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 5px; }
    .sub-header { font-size: 1rem; color: #888; margin-bottom: 20px; }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.05); padding: 24px; border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .m-label { color: #888; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
    .m-value { font-size: 2rem; font-weight: 700; margin-top: 8px; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important; color: white !important; border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

@st.cache_data(show_spinner=False)
def load_data(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        if "teachers" in filename: return pd.DataFrame(columns=["Teacher", "Department"])
        if "subjects" in filename: return pd.DataFrame(columns=["Subject", "Code"])
        if "curriculum" in filename: return pd.DataFrame(columns=["Teacher", "Subject", "Class", "Sessions"])
        return pd.DataFrame()
    return pd.read_csv(path)

def save_data(df, filename):
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)
    load_data.clear()

@st.cache_data(show_spinner=False)
def get_asc_styled_html(file_path):
    if not os.path.exists(file_path): return "File not found."
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    # (Simplified for brevity, use your previous HTML styling logic here)
    return str(soup)

# --- UI NAVIGATION ---
menu = st.sidebar.radio("Navigation", ["Overview", "Data Studio", "Generator", "Schedules"])

# ---------------- OVERVIEW ----------------
if menu == "Overview":
    st.markdown('<div class="main-header">Department Overview</div>', unsafe_allow_html=True)
    
    df_t = load_data("teachers.csv")
    df_cls = load_data("classes.csv")
    df_r = load_data("rooms.csv")
    df_curr = load_data("curriculum.csv")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><div class="m-label">Teachers</div><div class="m-value">{len(df_t)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="m-label">Classes</div><div class="m-value">{len(df_cls)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="m-label">Rooms</div><div class="m-value">{len(df_r)}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="m-label">Load</div><div class="m-value">{len(df_curr)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("👨‍🏫 Teacher Workload")
        if not df_curr.empty and "Teacher" in df_curr.columns:
            counts = df_curr['Teacher'].value_counts().reset_index()
            fig = px.bar(counts, x='Teacher', y='count', template="plotly_dark", color_discrete_sequence=['#3B82F6'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data in curriculum.csv. Go to Data Studio to add assignments.")

    with col_right:
        st.subheader("📚 Subject Distribution")
        if not df_curr.empty and "Subject" in df_curr.columns:
            counts = df_curr['Subject'].value_counts().reset_index()
            fig2 = px.pie(counts, values='count', names='Subject', template="plotly_dark", hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data in curriculum.csv.")

# ---------------- DATA STUDIO ----------------
elif menu == "Data Studio":
    st.markdown('<div class="main-header">Data Studio</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Infrastructure", "Curriculum"])

    with t1:
        st.write("Edit your basic resources below. Remember to click Save.")
        df_t = st.data_editor(load_data("teachers.csv"), num_rows="dynamic", key="et")
        if st.button("💾 Save Teachers"): save_data(df_t, "teachers.csv"); st.toast("Saved!")
        
        df_r = st.data_editor(load_data("rooms.csv"), num_rows="dynamic", key="er")
        if st.button("💾 Save Rooms"): save_data(df_r, "rooms.csv"); st.toast("Saved!")

    with t2:
        st.write("Assign Teachers to Classes and Subjects.")
        df_curr = st.data_editor(load_data("curriculum.csv"), num_rows="dynamic", key="ec")
        if st.button("💾 Save Curriculum"): save_data(df_curr, "curriculum.csv"); st.toast("Saved!")

# ---------------- GENERATOR (BUG FIXED HERE) ----------------
elif menu == "Generator":
    st.markdown('<div class="main-header">AI Generator</div>', unsafe_allow_html=True)
    
    if st.button("🚀 Run Scheduler", type="primary", use_container_width=True):
        if not BACKEND_AVAILABLE:
            st.error("Missing backend scripts (main.py or data_validator.py)")
        else:
            with st.status("Solving Timetable...", expanded=True) as status:
                try:
                    st.write("Step 1: Validating Data...")
                    data_validator.main() # Runs your validator
                    
                    st.write("Step 2: Solving Constraints...")
                    # --- FIX: We call 'solver_engine' because that's what we imported 'main' as ---
                    solver_engine.run() 
                    
                    status.update(label="Routine Generated!", state="complete")
                    st.balloons()
                except Exception as e:
                    status.update(label="Error Occurred", state="error")
                    st.error(f"Solver Error: {e}")

# ---------------- SCHEDULES ----------------
elif menu == "Schedules":
    st.markdown('<div class="main-header">Routine Hub</div>', unsafe_allow_html=True)
    if os.path.exists(OUTPUT_DIR):
        files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".html")]
        if files:
            target = st.selectbox("Select Timetable", sorted(files))
            html_content = get_asc_styled_html(os.path.join(OUTPUT_DIR, target))
            components.html(html_content, height=800, scrolling=True)
        else:
            st.info("No routines generated yet.")
