import streamlit as st
import pandas as pd
import os
import hashlib
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
import plotly.express as px

try:
    import main as solver_engine 
    import data_validator 
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

st.set_page_config(
    page_title="Cadence", 
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

DIRS = ["data", "output", "assets"]
for d in DIRS:
    os.makedirs(d, exist_ok=True)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header { 
        font-size: 2.2rem; font-weight: 800; 
        margin-bottom: 5px; 
    }
    .sub-header { font-size: 1rem; opacity: 0.7; margin-bottom: 25px; }

    .metric-container {
        padding: 20px; border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .m-label { opacity: 0.6; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }
    .m-value { font-size: 1.8rem; font-weight: 800; margin-top: 5px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

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
def get_asc_styled_html(file_path):
    if not os.path.exists(file_path): 
        return "<div>File not found.</div>"

    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    adaptive_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&display=swap');
        
        :root {
            --bg-color: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --header-bg: #f1f5f9;
            --card-bg: #ffffff;
            --border-color: #e2e8f0;
            --day-header-bg: #475569;
            --day-header-text: #ffffff;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: #0e1117;
                --text-primary: #f0f2f6;
                --text-secondary: #aeb5bc;
                --header-bg: #262730;
                --card-bg: #1f2937;
                --border-color: #374151;
                --day-header-bg: #1e293b;
                --day-header-text: #60a5fa;
            }
        }

        body { margin: 0; padding: 10px; font-family: 'Inter', sans-serif; background-color: transparent; }
        
        table { 
            width: 100%; border-collapse: separate; border-spacing: 6px; table-layout: fixed; 
        }
        
        th { 
            background-color: var(--header-bg); color: var(--text-secondary);
            padding: 12px; font-size: 11px; text-transform: uppercase; 
            border-radius: 6px; font-weight: 700;
        }

        .day-cell { 
            background-color: var(--day-header-bg) !important; color: var(--day-header-text) !important; 
            font-size: 16px; font-weight: 800; text-align: center; 
            vertical-align: middle; border-radius: 8px; width: 60px;
        }

        td { 
            height: 90px; vertical-align: top; padding: 8px; 
            background-color: var(--card-bg) !important;
            border-radius: 8px; 
            border: 1px solid var(--border-color);
            transition: transform 0.1s;
        }
        
        td:hover { transform: translateY(-2px); border-color: #3B82F6; }

        .card-content { display: flex; flex-direction: column; height: 100%; justify-content: space-between; }
        
        .subject-name { 
            font-size: 13px; font-weight: 800; color: var(--text-primary); line-height: 1.2; 
        }
        
        .meta-info { display: flex; gap: 4px; flex-wrap: wrap; margin-top: auto; }
        
        .badge { 
            font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 4px; 
        }
        .b-teacher { background: var(--header-bg); color: var(--text-secondary); }
        .b-room { background: #EFF6FF; color: #2563EB; }
        
        td:empty { background: transparent !important; border: 1px dashed var(--border-color); }
    </style>
    """

    def get_subject_color(name):
        h = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360
        return f"hsl({h}, 70%, 50%)" 

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

                accent = get_subject_color(subj)
                cell['style'] = f"border-left: 3px solid {accent};"

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

    return adaptive_css + str(soup)

logo_path = os.path.join("assets", "logo.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
    st.sidebar.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

menu = st.sidebar.radio("Navigation", ["Overview", "Data Studio", "Generator", "Schedules"])

if menu == "Overview":
    st.markdown('<div class="main-header">Department Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Summary of academic resources</div>', unsafe_allow_html=True)

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
        st.subheader("Teacher Workload")
        if not df_curr.empty and "Teacher" in df_curr.columns:
            load_counts = df_curr['Teacher'].value_counts().reset_index()
            load_counts.columns = ['Teacher', 'Count']
            fig = px.bar(load_counts, x='Teacher', y='Count')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No curriculum data.")

    with col2:
        st.subheader("Subject Distribution")
        if not df_curr.empty and "Subject" in df_curr.columns:
            sub_counts = df_curr['Subject'].value_counts().reset_index()
            fig2 = px.pie(sub_counts, values='count', names='Subject', hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No curriculum data.")

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
                html = get_asc_styled_html(path)
                st.components.v1.html(html, height=800, scrolling=True)
                with open(path, "rb") as f:
                    st.download_button("Download", f, file_name=sel_file)
        else:
            st.info("No files generated.")
