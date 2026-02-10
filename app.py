import streamlit as st
import pandas as pd
import os
import hashlib
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
import plotly.express as px

# --- 1. BACKEND INTEGRATION ---
try:
    import main as solver_engine 
    import data_validator 
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

# --- 2. INITIAL CONFIG ---
st.set_page_config(
    page_title="Cadence Scheduler", 
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize system directories
for d in ["data", "output", "assets"]:
    os.makedirs(d, exist_ok=True)

# --- 3. AGGRESSIVE LIGHT-MODE CSS (Fixes Black Menus) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Global Background Force */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }
    
    /* Sidebar Force */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }

    /* TYPOGRAPHY - Force black text on everything */
    h1, h2, h3, h4, h5, h6, p, li, span, div, label, .stMarkdown {
        color: #0F172A !important;
        font-family: 'Inter', sans-serif;
    }

    /* DROPDOWNS & SELECTBOXES - Fix for black menus */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="base-input"],
    [data-testid="stSelectbox"] div {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }
    
    /* Popover/Dropdown Menu list */
    div[data-baseweb="popover"], 
    div[data-baseweb="menu"],
    ul[role="listbox"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
    }
    
    li[role="option"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }
    
    li[role="option"]:hover {
        background-color: #F1F5F9 !important;
    }

    /* Metric Containers */
    .metric-container {
        background-color: #FFFFFF !important;
        padding: 20px; border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .m-label { color: #64748B !important; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }
    .m-value { font-size: 1.8rem; font-weight: 800; color: #0F172A !important; }

    /* Tabs UI */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; border-radius: 8px;
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0;
        color: #64748B !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
    }

    /* Data Editor / Dataframes */
    [data-testid="stDataFrame"] { background-color: #FFFFFF !important; }
    
    /* Hide specific Streamlit dark-mode icons */
    svg { fill: #475569 !important; }
</style>
""", unsafe_allow_html=True)

# --- 4. CORE UTILITIES ---

@st.cache_data(show_spinner=False)
def load_data(filename):
    path = os.path.join("data", filename)
    if not os.path.exists(path):
        if "teachers" in filename: return pd.DataFrame(columns=["Teacher", "Code"])
        if "subjects" in filename: return pd.DataFrame(columns=["Subject", "Category"])
        if "classes" in filename: return pd.DataFrame(columns=["Class_ID", "Grade"])
        if "rooms" in filename: return pd.DataFrame(columns=["Room_ID", "Type"])
        if "curriculum" in filename: return pd.DataFrame(columns=["Teacher", "Subject", "Class", "Sessions"])
        return pd.DataFrame()
    return pd.read_csv(path)

def save_data(df, filename):
    path = os.path.join("data", filename)
    df.to_csv(path, index=False)
    load_data.clear()

@st.cache_data(show_spinner=False)
def get_asc_styled_html(file_path, file_name):
    if not os.path.exists(file_path): return "<div>No routine found.</div>"

    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Injected Toolbar (Print + LocalSend Support)
    toolbar_js_css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&display=swap');
        body {{ margin: 0; padding: 20px; font-family: 'Inter', sans-serif; background-color: #FFFFFF; color: #000; }}
        
        .toolbar {{ 
            display: flex; gap: 10px; margin-bottom: 20px; 
            padding: 12px; background: #F8FAFC; border-radius: 10px; border: 1px solid #E2E8F0;
        }}
        .btn {{
            padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600;
            border: 1px solid #CBD5E1; cursor: pointer; display: flex; align-items: center; gap: 8px;
            background: white; color: #334155; transition: 0.2s;
        }}
        .btn:hover {{ background: #F1F5F9; transform: translateY(-1px); }}
        .btn-send {{ background: #000; color: #fff; border: none; }}

        table {{ width: 100%; border-collapse: separate; border-spacing: 6px; table-layout: fixed; }}
        th {{ background: #F1F5F9; color: #475569; padding: 12px; font-size: 11px; text-transform: uppercase; border-radius: 6px; font-weight: 700; }}
        .day-cell {{ background: #0F172A !important; color: white !important; font-size: 16px; font-weight: 800; text-align: center; vertical-align: middle; border-radius: 8px; width: 60px; }}
        td {{ height: 95px; vertical-align: top; padding: 8px; background: #FFF !important; border-radius: 8px; border: 1px solid #E2E8F0; }}
        
        .card-content {{ display: flex; flex-direction: column; height: 100%; justify-content: space-between; }}
        .subject-name {{ font-size: 13px; font-weight: 800; color: #1E293B; line-height: 1.2; }}
        .meta-info {{ display: flex; gap: 4px; flex-wrap: wrap; margin-top: auto; }}
        .badge {{ font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 4px; }}
        .b-teacher {{ background: #F1F5F9; color: #64748B; }}
        .b-room {{ background: #EFF6FF; color: #2563EB; }}

        @media print {{ .toolbar {{ display: none !important; }} body {{ padding: 0; }} * {{ -webkit-print-color-adjust: exact !important; }} }}
    </style>

    <div class="toolbar">
        <button onclick="window.print()" class="btn">📄 Save as PDF</button>
        <button onclick="localSendShare()" class="btn btn-send">📡 LocalSend / Share</button>
    </div>

    <script>
        async function localSendShare() {{
            const blob = new Blob([document.documentElement.outerHTML], {{ type: 'text/html' }});
            const file = new File([blob], "{file_name}", {{ type: 'text/html' }});
            if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                await navigator.share({{ files: [file], title: 'Routine Export' }});
            }} else {{ alert("Local sharing not supported in this browser."); }}
        }}
    </script>
    """

    def get_color(name):
        h = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360
        return f"hsl({h}, 85%, 96%)" 

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells: continue

        # Format Day Header
        if cells[0].get_text(strip=True) in ["Sa", "Su", "Mo", "Tu", "We", "Th", "Fr", "Saturday", "Sunday"]:
            cells[0]['class'] = 'day-cell'

        # Format Lesson Cards
        for cell in cells[1:]:
            parts = [p.strip() for p in cell.get_text(separator="|").split("|") if p.strip()]
            if parts:
                subj = parts[0]
                teacher = parts[1] if len(parts) > 1 else ""
                room = parts[2] if len(parts) > 2 else ""
                
                bg = get_color(subj)
                cell['style'] = f"background-color: {bg} !important; border-top: 3px solid hsl({int(hashlib.md5(subj.encode()).hexdigest(), 16) % 360}, 60%, 50%);"
                
                new_box = f"""
                <div class="card-content">
                    <div class="subject-name">{subj}</div>
                    <div class="meta-info">
                        <span class="badge b-teacher">{teacher}</span>
                        <span class="badge b-room">{room}</span>
                    </div>
                </div>
                """
                cell.clear()
                cell.append(BeautifulSoup(new_box, "html.parser"))

    return toolbar_js_css + str(soup)

# --- 5. UI VIEWS ---

# Sidebar Header
if os.path.exists("assets/logo.png"):
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("---")

menu = st.sidebar.radio("Navigation", ["Overview", "Data Studio", "Generator", "Schedules"])

if menu == "Overview":
    st.markdown('<div class="main-header">Department Overview</div>', unsafe_allow_html=True)
    
    df_t = load_data("teachers.csv")
    df_c = load_data("classes.csv")
    df_curr = load_data("curriculum.csv")
    df_r = load_data("rooms.csv")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-container"><div class="m-label">Faculty</div><div class="m-value">{len(df_t)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-container"><div class="m-label">Groups</div><div class="m-value">{len(df_c)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-container"><div class="m-label">Rooms</div><div class="m-value">{len(df_r)}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-container"><div class="m-label">Assignments</div><div class="m-value">{len(df_curr)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Teacher Workload")
        if not df_curr.empty and "Teacher" in df_curr.columns:
            fig = px.bar(df_curr['Teacher'].value_counts().reset_index(), x='Teacher', y='count', color_discrete_sequence=['#0F172A'])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.subheader("Subject Split")
        if not df_curr.empty and "Subject" in df_curr.columns:
            fig2 = px.pie(df_curr['Subject'].value_counts().reset_index(), values='count', names='Subject', hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

elif menu == "Data Studio":
    st.markdown('<div class="main-header">Data Studio</div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Infrastructure", "Curriculum", "Constraints"])

    with t1:
        c_l, c_r = st.columns(2)
        with c_l:
            st.write("**Teachers**")
            df_t = st.data_editor(load_data("teachers.csv"), num_rows="dynamic", key="dt", use_container_width=True)
            if st.button("💾 Save Teachers"): save_data(df_t, "teachers.csv"); st.toast("Saved")
            st.write("**Rooms**")
            df_r = st.data_editor(load_data("rooms.csv"), num_rows="dynamic", key="dr", use_container_width=True)
            if st.button("💾 Save Rooms"): save_data(df_r, "rooms.csv"); st.toast("Saved")
        with c_r:
            st.write("**Subjects**")
            df_s = st.data_editor(load_data("subjects.csv"), num_rows="dynamic", key="ds", use_container_width=True)
            if st.button("💾 Save Subjects"): save_data(df_s, "subjects.csv"); st.toast("Saved")
            st.write("**Classes**")
            df_c = st.data_editor(load_data("classes.csv"), num_rows="dynamic", key="dc", use_container_width=True)
            if st.button("💾 Save Classes"): save_data(df_c, "classes.csv"); st.toast("Saved")

    with t2:
        # Load lists for dropdowns
        t_list = load_data("teachers.csv").iloc[:,0].tolist() if not load_data("teachers.csv").empty else []
        s_list = load_data("subjects.csv").iloc[:,0].tolist() if not load_data("subjects.csv").empty else []
        c_list = load_data("classes.csv").iloc[:,0].tolist() if not load_data("classes.csv").empty else []
        
        cfg = {
            "Teacher": st.column_config.SelectboxColumn("Teacher", options=t_list, required=True),
            "Subject": st.column_config.SelectboxColumn("Subject", options=s_list, required=True),
            "Class": st.column_config.SelectboxColumn("Class", options=c_list, required=True)
        }
        df_curr = st.data_editor(load_data("curriculum.csv"), num_rows="dynamic", key="dcur", column_config=cfg, use_container_width=True)
        if st.button("💾 Save Curriculum", type="primary"): save_data(df_curr, "curriculum.csv"); st.toast("Saved")

    with t3:
        st.write("**Teacher Unavailability**")
        with st.expander("Restriction Wizard"):
            w_c1, w_c2 = st.columns(2)
            sel_t = w_c1.selectbox("Teacher", t_list) if t_list else None
            sel_d = w_c2.selectbox("Day", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Saturday"])
            if st.button("Add Constraint"):
                df_u = load_data("teacher_unavailability.csv")
                df_u = pd.concat([df_u, pd.DataFrame([{"Teacher": sel_t, "Day": sel_d, "Type": "Blocked"}])], ignore_index=True)
                save_data(df_u, "teacher_unavailability.csv"); st.success("Added")
        
        df_u = st.data_editor(load_data("teacher_unavailability.csv"), num_rows="dynamic", key="du", use_container_width=True)
        if st.button("💾 Save All Constraints"): save_data(df_u, "teacher_unavailability.csv"); st.toast("Saved")

elif menu == "Generator":
    st.markdown('<div class="main-header">Routine Generator</div>', unsafe_allow_html=True)
    if st.button("🚀 Run Solver Engine", type="primary", use_container_width=True):
        if BACKEND_AVAILABLE:
            with st.status("Computing schedules...", expanded=True) as s:
                try:
                    data_validator.main()
                    st.write("Validation passed.")
                    solver_engine.run() # Backend script execution
                    s.update(label="Routine Generated Successfully!", state="complete")
                    st.balloons()
                except Exception as e:
                    s.update(label="Engine Error", state="error")
                    st.error(str(e))
        else:
            st.error("Backend logic scripts (main.py/data_validator.py) not found.")

    if os.path.exists("warnings.log"):
        with st.expander("Validation Logs"):
            with open("warnings.log", "r") as f: st.code(f.read())

elif menu == "Schedules":
    st.markdown('<div class="main-header">Routine Hub</div>', unsafe_allow_html=True)
    if os.path.exists("output"):
        files = sorted([f for f in os.listdir("output") if f.endswith(".html")])
        if files:
            target = st.selectbox("Select Timetable", files)
            if target:
                full_path = os.path.join("output", target)
                styled_html = get_asc_styled_html(full_path, target)
                # Render UI
                st.components.v1.html(styled_html, height=850, scrolling=True)
                # Manual download fallback
                with open(full_path, "rb") as f:
                    st.download_button("📥 Download HTML File", f, file_name=target)
        else:
            st.info("No routine files found in output directory.")
