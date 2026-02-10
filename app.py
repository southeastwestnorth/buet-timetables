import streamlit as st
import pandas as pd
import os
import hashlib
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
import plotly.express as px

# --- ATTEMPT IMPORT OF LOGIC SCRIPTS ---
# We wrap this in try-except so the UI loads even if backend scripts are missing during setup
try:
    import main as engine # Logic script
    import data_validator # Validator script
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
# Ensure directories exist on startup to prevent crashes
DATA_DIR = "data"
OUTPUT_DIR = "output"
for d in [DATA_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

# --- CSS STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F8FAFC; }
    
    /* Headers */
    .main-header { font-size: 2rem; font-weight: 700; color: #0F172A; letter-spacing: -0.02em; }
    .sub-header { font-size: 1rem; color: #64748B; margin-bottom: 20px; }
    
    /* Metric Cards */
    .metric-card {
        background: white; padding: 24px; border-radius: 12px;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .m-label { color: #64748B; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    .m-value { font-size: 2rem; font-weight: 700; color: #0F172A; margin-top: 8px; }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; background-color: #FFFFFF; border-radius: 6px;
        border: 1px solid #E2E8F0; padding: 0 16px; font-weight: 500; color: #64748B;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important; color: white !important; border: 1px solid #2563EB;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS (CACHED) ---

@st.cache_data(show_spinner=False)
def load_data(filename):
    """Loads CSV data safely. Returns empty DF with standard columns if file missing."""
    path = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(path):
        # Return logical defaults to prevent KeyErrors in UI
        if "teachers" in filename: return pd.DataFrame(columns=["Teacher_ID", "Name", "Email"])
        if "subjects" in filename: return pd.DataFrame(columns=["Subject_ID", "Name", "Weekly_Hours"])
        if "rooms" in filename: return pd.DataFrame(columns=["Room_ID", "Capacity"])
        return pd.DataFrame()
        
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def save_data(df, filename):
    """Saves data and clears cache to ensure UI updates."""
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)
    load_data.clear() # Clear cache so next reload shows new data

@st.cache_data(show_spinner=False)
def get_asc_styled_html(file_path):
    """Parses raw HTML output and injects modern styling."""
    if not os.path.exists(file_path):
        return "<div style='padding:20px'>File not found.</div>"

    with open(file_path, 'r', encoding='utf-8') as f:
        raw_html = f.read()

    # CSS for the Timetable View
    asc_css = """
    <style>
        body { margin: 0; padding: 10px; font-family: 'Inter', sans-serif; }
        table { width: 100%; border-collapse: separate; border-spacing: 4px; table-layout: fixed; }
        th { background: #F1F5F9; color: #475569; padding: 10px; font-size: 12px; border-radius: 6px; }
        td { height: 90px; vertical-align: top; padding: 6px; border-radius: 6px; border: 1px solid #E2E8F0; background: #FFF; font-size: 12px; }
        .day-cell { background: #334155 !important; color: white !important; font-weight: 700; width: 50px; text-align: center; vertical-align: middle; }
        .cell-content { display: flex; flex-direction: column; height: 100%; justify-content: space-between; }
        .subj { font-weight: 700; color: #1E293B; }
        .meta { display: flex; justify-content: space-between; margin-top: 4px; }
        .tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
        .teacher { background: #F1F5F9; color: #64748B; }
        .room { background: #EFF6FF; color: #2563EB; }
    </style>
    """

    def get_color(name):
        h = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360
        return f"hsla({h}, 70%, 96%, 1)"

    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Process Table
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells: continue
        
        # Style first column (Days)
        cells[0]['class'] = 'day-cell'
        
        # Style Data Cells
        for cell in cells[1:]:
            subj_tag = cell.find("span", class_="subject-id") # Adjust class names based on your output
            
            if subj_tag:
                subj = subj_tag.get_text(strip=True)
                teacher = cell.find("div", class_="teacher-id").get_text(strip=True) if cell.find("div", class_="teacher-id") else ""
                room = cell.find("div", class_="room-info").get_text(strip=True) if cell.find("div", class_="room-info") else ""
                
                cell['style'] = f"background-color: {get_color(subj)}; border-color: {get_color(subj).replace('96%', '80%')}"
                
                new_html = f"""
                <div class="cell-content">
                    <div class="subj">{subj}</div>
                    <div class="meta">
                        <span class="tag teacher">{teacher}</span>
                        <span class="tag room">{room}</span>
                    </div>
                </div>
                """
                cell.clear()
                cell.append(BeautifulSoup(new_html, "html.parser"))

    return asc_css + str(soup)

# --- UI LAYOUT ---

menu = st.sidebar.radio("Navigation", ["Overview", "Data Studio", "Generator", "Schedules"])

# ---------------- OVERVIEW ----------------
if menu == "Overview":
    st.markdown('<div class="main-header">Department Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Dashboard & Resource Summary</div>', unsafe_allow_html=True)

    # Metrics
    df_t = load_data("teachers.csv")
    df_c = load_data("classes.csv")
    df_r = load_data("rooms.csv")
    df_curr = load_data("curriculum.csv")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><div class="m-label">Teachers</div><div class="m-value">{len(df_t)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="m-label">Classes</div><div class="m-value">{len(df_c)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="m-label">Rooms</div><div class="m-value">{len(df_r)}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="m-label">Assignments</div><div class="m-value">{len(df_curr)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # Visual Analytics
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("👨‍🏫 Teacher Workload")
        if not df_curr.empty and "Teacher" in df_curr.columns:
            load_counts = df_curr['Teacher'].value_counts().reset_index()
            load_counts.columns = ['Teacher', 'Count']
            fig = px.bar(load_counts, x='Teacher', y='Count', color='Count', color_continuous_scale='Blues')
            fig.update_layout(xaxis_title=None, height=350, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add curriculum data to see workload analytics.")

    with col_right:
        st.subheader("📚 Subject Distribution")
        if not df_curr.empty and "Subject" in df_curr.columns:
            sub_counts = df_curr['Subject'].value_counts().reset_index()
            sub_counts.columns = ['Subject', 'Count']
            fig2 = px.pie(sub_counts, values='Count', names='Subject', hole=0.5)
            fig2.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Add curriculum data to see subject analytics.")

# ---------------- DATA STUDIO ----------------
elif menu == "Data Studio":
    st.markdown('<div class="main-header">Data Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage academic resources and constraints</div>', unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["Infrastructure", "Curriculum", "Constraints"])

    with t1:
        c_left, c_right = st.columns([1,1])
        with c_left:
            st.write("**Teachers**")
            df_t = st.data_editor(load_data("teachers.csv"), num_rows="dynamic", key="dt", use_container_width=True)
            if st.button("💾 Save Teachers", use_container_width=True):
                save_data(df_t, "teachers.csv"); st.toast("Saved!")

            st.write("**Rooms**")
            df_r = st.data_editor(load_data("rooms.csv"), num_rows="dynamic", key="dr", use_container_width=True)
            if st.button("💾 Save Rooms", use_container_width=True):
                save_data(df_r, "rooms.csv"); st.toast("Saved!")

        with c_right:
            st.write("**Subjects**")
            df_sub = st.data_editor(load_data("subjects.csv"), num_rows="dynamic", key="dsub", use_container_width=True)
            if st.button("💾 Save Subjects", use_container_width=True):
                save_data(df_sub, "subjects.csv"); st.toast("Saved!")
                
            st.write("**Classes/Groups**")
            df_cls = st.data_editor(load_data("classes.csv"), num_rows="dynamic", key="dcls", use_container_width=True)
            if st.button("💾 Save Classes", use_container_width=True):
                save_data(df_cls, "classes.csv"); st.toast("Saved!")

    with t2:
        st.info("💡 Tip: Defines which teacher teaches what subject to which class.")
        
        # Load Reference Lists for Dropdowns
        teachers_list = load_data("teachers.csv").iloc[:, 0].tolist() if not load_data("teachers.csv").empty else []
        subjects_list = load_data("subjects.csv").iloc[:, 0].tolist() if not load_data("subjects.csv").empty else []
        classes_list = load_data("classes.csv").iloc[:, 0].tolist() if not load_data("classes.csv").empty else []
        
        # Configure Dropdowns for Data Integrity
        col_config = {
            "Teacher": st.column_config.SelectboxColumn("Teacher", options=teachers_list, required=True),
            "Subject": st.column_config.SelectboxColumn("Subject", options=subjects_list, required=True),
            "Class": st.column_config.SelectboxColumn("Class", options=classes_list, required=True),
            "Sessions_Per_Week": st.column_config.NumberColumn("Sessions", min_value=1, max_value=10)
        }

        df_c = st.data_editor(
            load_data("curriculum.csv"), 
            num_rows="dynamic", 
            key="dc", 
            use_container_width=True,
            column_config=col_config
        )
        if st.button("💾 Save Curriculum", type="primary"):
            save_data(df_c, "curriculum.csv"); st.toast("Curriculum Saved!")

    with t3:
        st.write("**Teacher Unavailability**")
        
        # Helper Wizard for Constraints
        with st.expander("➕ Add Unavailability Rule (Wizard)"):
            c_wiz1, c_wiz2 = st.columns(2)
            w_teacher = c_wiz1.selectbox("Teacher", teachers_list) if teachers_list else None
            w_day = c_wiz2.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            if st.button("Add Rule"):
                new_row = pd.DataFrame([{"Teacher": w_teacher, "Day": w_day, "Type": "Unavailable"}])
                df_u = pd.concat([load_data("teacher_unavailability.csv"), new_row], ignore_index=True)
                save_data(df_u, "teacher_unavailability.csv")
                st.success("Rule Added!")

        df_u = st.data_editor(load_data("teacher_unavailability.csv"), num_rows="dynamic", key="du", use_container_width=True)
        if st.button("💾 Save Constraints"):
            save_data(df_u, "teacher_unavailability.csv"); st.toast("Saved!")

# ---------------- GENERATOR ----------------
elif menu == "Generator":
    st.markdown('<div class="main-header">AI Generator</div>', unsafe_allow_html=True)
    
    col_gen, col_log = st.columns([1, 1])
    
    with col_gen:
        st.markdown("""
        <div style="background:white; padding:20px; border-radius:10px; border:1px solid #ddd;">
            <h4>🚀 Launch Scheduler</h4>
            <p style="color:#666; font-size:14px;">This utilizes the Google OR-Tools engine to find the optimal schedule based on the constraints defined in Data Studio.</p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        if not BACKEND_AVAILABLE:
            st.error("❌ Backend scripts (`main.py` or `data_validator.py`) are missing.")
        else:
            if st.button("Run Computation Engine", type="primary", use_container_width=True):
                with st.status("⚙️ Engine Running...", expanded=True) as status:
                    st.write("🔍 Validating Data Integrity...")
                    try:
                        data_validator.main()
                        st.write("✅ Validation Passed.")
                    except Exception as e:
                        status.update(label="Validation Failed", state="error")
                        st.error(f"Validator Error: {e}")
                        st.stop()

                    st.write("🧮 Solving Constraint Model (CP-SAT)...")
                    try:
                        # Capture output logic here ideally, assuming main.run() saves files
                        main.run()
                        status.update(label="Schedule Generated Successfully!", state="complete")
                        st.balloons()
                    except Exception as e:
                        status.update(label="Solver Failed", state="error")
                        st.error(f"Solver Error: {e}")

    with col_log:
        st.write("**System Logs**")
        log_path = "warnings.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                logs = f.read()
            if logs:
                st.warning("⚠️ Validation Warnings")
                st.code(logs, language="text")
            else:
                st.success("✅ System Clean. No warnings.")
        else:
            st.info("No logs available yet.")

# ---------------- SCHEDULES ----------------
elif menu == "Schedules":
    st.markdown('<div class="main-header">Routine Hub</div>', unsafe_allow_html=True)
    
    if not os.path.exists(OUTPUT_DIR):
        st.error("Output directory missing.")
    else:
        files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".html")]
        
        if files:
            c_sel, c_ref = st.columns([3, 1])
            with c_sel:
                target = st.selectbox("Select Timetable", sorted(files, reverse=True))
            with c_ref:
                st.write("") # spacer
                st.write("") # spacer
                if st.button("🔄 Refresh List"):
                    st.rerun()

            if target:
                styled_html = get_asc_styled_html(os.path.join(OUTPUT_DIR, target))
                
                # Download Handler
                st.download_button(
                    label="📥 Download HTML Report",
                    data=styled_html,
                    file_name=target,
                    mime="text/html"
                )
                
                # Display
                st.components.v1.html(styled_html, height=800, scrolling=True)
        else:
            st.container().warning("No schedules found. Go to 'Generator' to create one.")
