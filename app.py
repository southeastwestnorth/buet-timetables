import streamlit as st
import pandas as pd
import os
import hashlib
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
import plotly.express as px
import base64

# --- BACKEND CHECK ---
try:
    import main as solver_engine 
    import data_validator 
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

# --- CONFIG ---
st.set_page_config(
    page_title="Cadence", 
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

DIRS = ["data", "output", "assets"]
for d in DIRS:
    os.makedirs(d, exist_ok=True)

# --- CSS: FORCE LIGHT THEME & STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* FORCE LIGHT MODE BACKGROUNDS */
    [data-testid="stAppViewContainer"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid="stHeader"] {
        background-color: rgba(255,255,255,0.9) !important;
    }
    
    /* Text Overrides */
    h1, h2, h3, h4, h5, h6, p, li, span, div, label {
        color: #0F172A !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Metric Cards */
    .metric-container {
        background-color: #FFFFFF !important;
        padding: 20px; border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .m-label { color: #64748B !important; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }
    .m-value { font-size: 1.8rem; font-weight: 800; color: #0F172A !important; margin-top: 5px; }

    /* Tabs */
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
    
    /* Tables & Inputs */
    [data-testid="stDataFrame"] { background-color: #FFFFFF !important; }
    div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: black; }
</style>
""", unsafe_allow_html=True)

# --- HELPERS ---

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
    """
    Injects JS that creates a real file object for LocalSend/System Share.
    """
    if not os.path.exists(file_path): return "<div>File not found.</div>"

    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # CLEAN JS FOR FILE SHARING & PRINTING
    enhanced_html = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&display=swap');
        
        body {{ margin: 0; padding: 20px; font-family: 'Inter', sans-serif; background-color: #FFFFFF; }}
        
        /* Toolbar */
        .toolbar {{ 
            display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;
            padding: 12px; background: #F1F5F9; border-radius: 10px; border: 1px solid #E2E8F0;
            align-items: center; justify-content: space-between;
        }}
        .tool-group {{ display: flex; gap: 10px; }}
        
        .btn {{
            padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600;
            border: 1px solid #CBD5E1; cursor: pointer; display: flex; align-items: center; gap: 8px;
            background: white; color: #334155; transition: 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }}
        .btn:hover {{ background: #F8FAFC; border-color: #64748B; transform: translateY(-1px); }}
        
        .btn-primary {{ background: #0F172A; color: white; border-color: #0F172A; }}
        .btn-primary:hover {{ background: #334155; color: white; }}
        
        .btn-share {{ background: #ff7e5f; color: white; border: none; background: linear-gradient(90deg, #ff7e5f, #feb47b); }}
        .btn-share:hover {{ opacity: 0.9; }}

        /* Table Styling */
        table {{ width: 100%; border-collapse: separate; border-spacing: 6px; table-layout: fixed; }}
        
        th {{ 
            background-color: #F1F5F9; color: #475569;
            padding: 12px; font-size: 11px; text-transform: uppercase; 
            border-radius: 6px; font-weight: 700;
        }}

        .day-cell {{ 
            background-color: #334155 !important; color: white !important; 
            font-size: 16px; font-weight: 800; text-align: center; 
            vertical-align: middle; border-radius: 8px; width: 60px;
        }}

        td {{ 
            height: 95px; vertical-align: top; padding: 8px; 
            background-color: #FFFFFF !important;
            border-radius: 8px; 
            border: 1px solid #E2E8F0;
        }}
        
        .card-content {{ display: flex; flex-direction: column; height: 100%; justify-content: space-between; }}
        .subject-name {{ font-size: 13px; font-weight: 800; color: #1E293B; line-height: 1.2; }}
        .meta-info {{ display: flex; gap: 4px; flex-wrap: wrap; margin-top: auto; }}
        .badge {{ font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 4px; }}
        .b-teacher {{ background: #F1F5F9; color: #64748B; }}
        .b-room {{ background: #EFF6FF; color: #2563EB; }}

        /* Print Specifics */
        @media print {{
            .toolbar {{ display: none !important; }}
            body {{ padding: 0; }}
            td {{ border: 1px solid #ccc !important; }}
            /* Ensure background colors print */
            * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        }}
    </style>

    <div class="toolbar">
        <div class="tool-group">
            <button onclick="window.print()" class="btn">
                📄 Print / Save PDF
            </button>
        </div>
        <div class="tool-group">
            <!-- This triggers the native share sheet which LocalSend uses -->
            <button onclick="shareFile()" class="btn btn-share">
                <span style="font-size: 1.2em;">📡</span> Local Share / LocalSend
            </button>
        </div>
    </div>

    <script>
        async function shareFile() {{
            // 1. Get HTML Content
            const htmlContent = document.documentElement.outerHTML;
            
            // 2. Create a Blob (File Object)
            const blob = new Blob([htmlContent], {{ type: 'text/html' }});
            
            // 3. Create a File object (needed for LocalSend detection)
            const file = new File([blob], "{file_name}", {{ type: 'text/html' }});

            // 4. Trigger Native Share
            if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                try {{
                    await navigator.share({{
                        files: [file],
                        title: 'Class Routine',
                        text: 'Sharing class routine file.'
                    }});
                }} catch (error) {{
                    console.log('Share failed or canceled', error);
                }}
            }} else {{
                alert("Native file sharing not supported on this browser. Please use the Download button below and drag the file to LocalSend.");
            }}
        }}
    </script>
    """

    def get_color(name):
        h = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360
        return f"hsl({h}, 80%, 96%)" 

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells: continue

        if cells[0].get_text(strip=True) in ["Sa", "Su", "Mo", "Tu", "We", "Th", "Fr", "Saturday", "Sunday"]:
            cells[0]['class'] = 'day-cell'

        for cell in cells[1:]:
            text_content = [t.strip() for t in cell.get_text(separator="|").split("|") if t.strip()]
            
            if len(text_content) >= 1:
                subj = text_content[0]
                teacher = text_content[1] if len(text_content) > 1 else ""
                room = text_content[2] if len(text_content) > 2 else ""

                bg = get_color(subj)
                cell['style'] = f"background-color: {bg} !important; border-top: 3px solid hsl({int(hashlib.md5(subj.encode()).hexdigest(), 16) % 360}, 60%, 60%);"

                new_html = f"""
                <div class="card-content">
                    <div class="subject-name">{subj}</div>
                    <div class="meta-info">
                        <span class="badge b-teacher">{teacher}</span>
                        <span class="badge b-room">{room}</span>
                    </div>
                </div>
                """
                cell.clear()
                cell.append(BeautifulSoup(new_html, "html.parser"))

    return enhanced_html + str(soup)

# --- UI START ---

# Sidebar Logo
logo_path = os.path.join("assets", "logo.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
    st.sidebar.markdown("---")

menu = st.sidebar.radio("Navigation", ["Overview", "Data Studio", "Generator", "Schedules"])

if menu == "Overview":
    st.markdown('<div class="main-header">Department Overview</div>', unsafe_allow_html=True)
    
    df_t = load_data("teachers.csv")
    df_c = load_data("classes.csv")
    df_curr = load_data("curriculum.csv")
    df_r = load_data("rooms.csv")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-container"><div class="m-label">Teachers</div><div class="m-value">{len(df_t)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-container"><div class="m-label">Classes</div><div class="m-value">{len(df_c)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-container"><div class="m-label">Rooms</div><div class="m-value">{len(df_r)}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-container"><div class="m-label">Load</div><div class="m-value">{len(df_curr)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Workload")
        if not df_curr.empty and "Teacher" in df_curr.columns:
            load_counts = df_curr['Teacher'].value_counts().reset_index()
            load_counts.columns = ['Teacher', 'Count']
            fig = px.bar(load_counts, x='Teacher', y='Count')
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No curriculum data found.")

    with col2:
        st.subheader("Subjects")
        if not df_curr.empty and "Subject" in df_curr.columns:
            sub_counts = df_curr['Subject'].value_counts().reset_index()
            fig2 = px.pie(sub_counts, values='count', names='Subject', hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No curriculum data found.")

elif menu == "Data Studio":
    st.markdown('<div class="main-header">Data Studio</div>', unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["Infrastructure", "Curriculum", "Constraints"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Teachers**")
            df_t = st.data_editor(load_data("teachers.csv"), num_rows="dynamic", key="dt", use_container_width=True)
            if st.button("💾 Save Teachers"): save_data(df_t, "teachers.csv"); st.toast("Saved")
            
            st.write("**Rooms**")
            df_r = st.data_editor(load_data("rooms.csv"), num_rows="dynamic", key="dr", use_container_width=True)
            if st.button("💾 Save Rooms"): save_data(df_r, "rooms.csv"); st.toast("Saved")
        
        with c2:
            st.write("**Subjects**")
            df_s = st.data_editor(load_data("subjects.csv"), num_rows="dynamic", key="ds", use_container_width=True)
            if st.button("💾 Save Subjects"): save_data(df_s, "subjects.csv"); st.toast("Saved")
            
            st.write("**Classes**")
            df_c = st.data_editor(load_data("classes.csv"), num_rows="dynamic", key="dc", use_container_width=True)
            if st.button("💾 Save Classes"): save_data(df_c, "classes.csv"); st.toast("Saved")

    with t2:
        teachers = load_data("teachers.csv").iloc[:, 0].tolist() if not load_data("teachers.csv").empty else []
        subjects = load_data("subjects.csv").iloc[:, 0].tolist() if not load_data("subjects.csv").empty else []
        classes = load_data("classes.csv").iloc[:, 0].tolist() if not load_data("classes.csv").empty else []
        
        col_config = {
            "Teacher": st.column_config.SelectboxColumn("Teacher", options=teachers, required=True),
            "Subject": st.column_config.SelectboxColumn("Subject", options=subjects, required=True),
            "Class": st.column_config.SelectboxColumn("Class", options=classes, required=True),
            "Sessions": st.column_config.NumberColumn("Sessions", min_value=1, max_value=10, default=3)
        }
        
        df_curr = st.data_editor(
            load_data("curriculum.csv"), 
            num_rows="dynamic", 
            key="dc", 
            column_config=col_config, 
            use_container_width=True
        )
        if st.button("💾 Save Curriculum", type="primary"): 
            save_data(df_curr, "curriculum.csv"); st.toast("Saved")

    with t3:
        st.write("Teacher Unavailability")
        with st.expander("Add Restriction Wizard"):
            c1, c2 = st.columns(2)
            sel_t = c1.selectbox("Teacher", teachers) if teachers else None
            sel_d = c2.selectbox("Day", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
            if st.button("Add"):
                df_u = load_data("teacher_unavailability.csv")
                new_row = pd.DataFrame([{"Teacher": sel_t, "Day": sel_d, "Type": "Unavailable"}])
                df_u = pd.concat([df_u, new_row], ignore_index=True)
                save_data(df_u, "teacher_unavailability.csv")
                st.success("Added")
        
        df_u = st.data_editor(load_data("teacher_unavailability.csv"), num_rows="dynamic", key="du", use_container_width=True)
        if st.button("💾 Save Constraints"): save_data(df_u, "teacher_unavailability.csv"); st.toast("Saved")

elif menu == "Generator":
    st.markdown('<div class="main-header">Generator</div>', unsafe_allow_html=True)
    
    if st.button("Run Scheduler", type="primary", use_container_width=True):
        if BACKEND_AVAILABLE:
            with st.status("Running...", expanded=True) as status:
                try:
                    data_validator.main()
                    st.write("Validation passed.")
                    solver_engine.run()
                    status.update(label="Complete!", state="complete")
                    st.balloons()
                except Exception as e:
                    status.update(label="Error", state="error")
                    st.error(str(e))
        else:
            st.error("Backend modules not found.")

    if os.path.exists("warnings.log"):
        with st.expander("View Logs"):
            with open("warnings.log", "r") as f:
                st.code(f.read())

elif menu == "Schedules":
    st.markdown('<div class="main-header">Schedules</div>', unsafe_allow_html=True)
    
    if os.path.exists("output"):
        files = sorted([f for f in os.listdir("output") if f.endswith(".html")])
        if files:
            sel_file = st.selectbox("Select File", files)
            if sel_file:
                path = os.path.join("output", sel_file)
                html = get_asc_styled_html(path, sel_file)
                
                # Render the High Quality HTML
                st.components.v1.html(html, height=800, scrolling=True)
                
                # Download Button for Manual LocalSend usage
                with open(path, "rb") as f:
                    st.download_button("📥 Download HTML Source", f, file_name=sel_file)
        else:
            st.info("No files generated.")
