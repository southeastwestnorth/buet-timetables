import streamlit as st
import pandas as pd
import os
import hashlib
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
import plotly.express as px
import plotly.graph_objects as go

# --- 1. BACKEND CONNECTION ---
# We wrap imports to prevent the app from crashing if logic scripts aren't ready yet
try:
    import main as solver_engine 
    import data_validator 
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

# --- 2. CONFIGURATION ---
st.set_page_config(
    page_title="Cadence Scheduler", 
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 3. ASSETS & DIRECTORIES ---
DIRS = ["data", "output", "assets"]
for d in DIRS:
    os.makedirs(d, exist_ok=True)

# --- 4. GLOBAL STYLING (MODERN & DARK MODE READY) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Modern Header Styling */
    .main-header { 
        font-size: 2.2rem; font-weight: 800; 
        background: linear-gradient(90deg, #FFFFFF, #94A3B8);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 5px; 
    }
    .sub-header { font-size: 1rem; color: #94A3B8; margin-bottom: 25px; }

    /* Glassmorphism Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.03); 
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 16px;
        transition: transform 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-5px); border-color: #3B82F6; }
    
    .m-label { color: #64748B; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .m-value { font-size: 2.2rem; font-weight: 800; color: #F8FAFC; margin-top: 5px; }
    
    /* Custom Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; background-color: rgba(255,255,255,0.05); border-radius: 8px;
        color: #CBD5E1; border: none; font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3B82F6 !important; color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 5. LOGIC & CACHING ---

@st.cache_data(show_spinner=False)
def load_data(filename):
    """Safely loads CSVs. Returns structure even if file is missing."""
    path = os.path.join("data", filename)
    if not os.path.exists(path):
        # Return intelligent defaults so the UI doesn't break
        if "teachers" in filename: return pd.DataFrame(columns=["Teacher", "Code"])
        if "subjects" in filename: return pd.DataFrame(columns=["Subject", "Category"])
        if "classes" in filename: return pd.DataFrame(columns=["Class_ID", "Grade"])
        if "rooms" in filename: return pd.DataFrame(columns=["Room_ID", "Type"])
        if "curriculum" in filename: return pd.DataFrame(columns=["Teacher", "Subject", "Class", "Sessions"])
        return pd.DataFrame()
    return pd.read_csv(path)

def save_data(df, filename):
    """Saves CSV and busts cache."""
    path = os.path.join("data", filename)
    df.to_csv(path, index=False)
    load_data.clear()

@st.cache_data(show_spinner=False)
def get_asc_styled_html(file_path):
    """
    Parses the raw HTML timetable and injects high-contrast CSS 
    so it looks like a dashboard widget, not an old excel sheet.
    """
    if not os.path.exists(file_path): 
        return "<div style='color:red; padding:20px;'>File not found. Please regenerate.</div>"

    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # --- THE MODERNIFICATION CSS ---
    # This forces the table to look good regardless of Streamlit's Dark/Light mode
    modern_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&display=swap');
        body { margin: 0; padding: 10px; font-family: 'Inter', sans-serif; background: transparent; }
        
        table { 
            width: 100%; border-collapse: separate; border-spacing: 8px; table-layout: fixed; 
        }
        
        /* Headers (Periods) */
        th { 
            background: #1E293B; color: #94A3B8; padding: 12px; 
            font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
            border-radius: 6px; font-weight: 700;
        }

        /* Day Column (Left) */
        .day-cell { 
            background: #0F172A !important; color: #3B82F6 !important; 
            font-size: 18px; font-weight: 800; text-align: center; 
            vertical-align: middle; border-radius: 8px; width: 60px;
        }

        /* The Lesson Card */
        td { 
            height: 95px; vertical-align: top; padding: 8px; 
            background: #FFFFFF !important; /* Force White Card */
            border-radius: 8px; 
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            transition: transform 0.1s;
        }
        td:hover { transform: scale(1.02); z-index: 10; border-color: #3B82F6; }

        /* Content Typography */
        .card-content { display: flex; flex-direction: column; height: 100%; justify-content: space-between; }
        .subject-name { 
            font-size: 13px; font-weight: 800; color: #1E293B; line-height: 1.2; 
        }
        .meta-info { display: flex; gap: 4px; flex-wrap: wrap; margin-top: auto; }
        .badge { 
            font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 4px; 
        }
        .b-teacher { background: #F1F5F9; color: #64748B; }
        .b-room { background: #EFF6FF; color: #2563EB; }
        
        /* Empty Cells */
        td:empty { background: rgba(255,255,255,0.03) !important; border: 1px dashed #334155; box-shadow: none; }
    </style>
    """

    def get_subject_color(name):
        # Consistent pastel color generator
        h = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360
        return f"hsl({h}, 85%, 96%)"

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells: continue

        # 1. Identify Day Headers (Sa, Su, Mo...)
        # We assume the first column is the day
        if cells[0].get_text(strip=True) in ["Sa", "Su", "Mo", "Tu", "We", "Th", "Fr", "Saturday", "Sunday"]:
            cells[0]['class'] = 'day-cell'

        # 2. Process Data Cells
        for cell in cells[1:]:
            # Extract text elements. aSc usually puts them in spans or raw text
            # We treat the text content as [Subject, Teacher, Room] roughly
            text_content = [t.strip() for t in cell.get_text(separator="|").split("|") if t.strip()]
            
            if len(text_content) >= 1:
                subj = text_content[0]
                # Try to guess teacher/room from remaining text, or leave blank
                teacher = text_content[1] if len(text_content) > 1 else ""
                room = text_content[2] if len(text_content) > 2 else ""

                # Colorize the card border based on subject
                bg_color = get_subject_color(subj)
                cell['style'] = f"background-color: {bg_color} !important; border-top: 3px solid hsl({int(hashlib.md5(subj.encode()).hexdigest(), 16) % 360}, 60%, 60%);"

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

    return modern_css + str(soup)

# --- 6. MAIN UI ---

# Sidebar Logo
logo_path = os.path.join("assets", "logo.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
    st.sidebar.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

menu = st.sidebar.radio("Main Menu", ["Dashboard", "Data Studio", "Generator", "Schedules"])

# --- TAB: DASHBOARD ---
if menu == "Dashboard":
    st.markdown('<div class="main-header">Cadence Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Overview of your academic infrastructure</div>', unsafe_allow_html=True)

    # Load Data
    df_t = load_data("teachers.csv")
    df_c = load_data("classes.csv")
    df_curr = load_data("curriculum.csv")
    df_r = load_data("rooms.csv")

    # Metrics Row
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><div class="m-label">Faculty</div><div class="m-value">{len(df_t)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="m-label">Classes</div><div class="m-value">{len(df_c)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="m-label">Total Load</div><div class="m-value">{len(df_curr)}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="m-label">Rooms</div><div class="m-value">{len(df_r)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Charts Row
    g1, g2 = st.columns([2, 1])
    
    with g1:
        st.subheader("📊 Teacher Workload Analysis")
        if not df_curr.empty and "Teacher" in df_curr.columns:
            # Calculate sessions per teacher
            load_data_viz = df_curr.groupby("Teacher").sum(numeric_only=True).reset_index()
            # If Sessions column exists, use it, else count rows
            if "Sessions" in df_curr.columns:
                y_val = "Sessions"
            else:
                load_data_viz = df_curr['Teacher'].value_counts().reset_index()
                load_data_viz.columns = ["Teacher", "Sessions"]
                y_val = "Sessions"

            fig = px.bar(
                load_data_viz, x="Teacher", y=y_val, 
                color=y_val, 
                color_continuous_scale="Turbo", # High contrast neon style
                template="plotly_dark"
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Assign subjects in 'Data Studio' to see workload charts.")

    with g2:
        st.subheader("⚠️ System Health")
        # Logic: Check if there are subjects in the list that aren't assigned
        df_sub = load_data("subjects.csv")
        if not df_sub.empty and not df_curr.empty:
            all_subjects = set(df_sub.iloc[:,0]) # Assume first col is Name
            assigned_subjects = set(df_curr["Subject"]) if "Subject" in df_curr.columns else set()
            orphaned = len(all_subjects - assigned_subjects)
            
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px;">
                <h3 style="margin:0; color:#F87171;">{orphaned}</h3>
                <p style="color:#94A3B8; font-size:12px;">Unassigned Subjects</p>
            </div>
            """, unsafe_allow_html=True)
            
            if orphaned > 0:
                st.warning(f"{orphaned} subjects have no teacher assigned.")
        else:
            st.write("No data to analyze.")

# --- TAB: DATA STUDIO ---
elif menu == "Data Studio":
    st.markdown('<div class="main-header">Data Studio</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🏛️ Infrastructure", "📚 Curriculum", "🚫 Constraints"])

    with tab1:
        col_infra_1, col_infra_2 = st.columns(2)
        with col_infra_1:
            st.caption("Teachers Directory")
            df_t = st.data_editor(load_data("teachers.csv"), num_rows="dynamic", key="dt", use_container_width=True)
            if st.button("💾 Save Teachers"): save_data(df_t, "teachers.csv"); st.toast("Teachers Saved")

            st.caption("Classrooms")
            df_r = st.data_editor(load_data("rooms.csv"), num_rows="dynamic", key="dr", use_container_width=True)
            if st.button("💾 Save Rooms"): save_data(df_r, "rooms.csv"); st.toast("Rooms Saved")
            
        with col_infra_2:
            st.caption("Subjects List")
            df_s = st.data_editor(load_data("subjects.csv"), num_rows="dynamic", key="ds", use_container_width=True)
            if st.button("💾 Save Subjects"): save_data(df_s, "subjects.csv"); st.toast("Subjects Saved")
            
            st.caption("Classes / Sections")
            df_c = st.data_editor(load_data("classes.csv"), num_rows="dynamic", key="dc", use_container_width=True)
            if st.button("💾 Save Classes"): save_data(df_c, "classes.csv"); st.toast("Classes Saved")

    with tab2:
        st.info("ℹ️ Defines who teaches what. Ensure 'Teacher' and 'Subject' names match the lists in Infrastructure.")
        
        # Foreign Key Dropdowns
        teachers_list = load_data("teachers.csv").iloc[:, 0].tolist() if not load_data("teachers.csv").empty else []
        subjects_list = load_data("subjects.csv").iloc[:, 0].tolist() if not load_data("subjects.csv").empty else []
        classes_list = load_data("classes.csv").iloc[:, 0].tolist() if not load_data("classes.csv").empty else []

        col_config = {
            "Teacher": st.column_config.SelectboxColumn("Teacher", options=teachers_list, required=True),
            "Subject": st.column_config.SelectboxColumn("Subject", options=subjects_list, required=True),
            "Class": st.column_config.SelectboxColumn("Class", options=classes_list, required=True),
            "Sessions": st.column_config.NumberColumn("Sessions/Week", min_value=1, max_value=10, default=3)
        }

        df_curr = st.data_editor(
            load_data("curriculum.csv"), 
            num_rows="dynamic", 
            key="d_curr", 
            column_config=col_config,
            use_container_width=True
        )
        if st.button("💾 Save Curriculum", type="primary"): 
            save_data(df_curr, "curriculum.csv"); st.toast("Curriculum Saved")

    with tab3:
        st.write("Define when teachers are **NOT** available.")
        
        # Simple Wizard to add constraints
        with st.expander("🪄 Constraint Wizard (Quick Add)"):
            c1, c2, c3 = st.columns(3)
            w_t = c1.selectbox("Who?", teachers_list) if teachers_list else None
            w_d = c2.selectbox("When?", ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday"])
            if st.button("Add Restriction"):
                df_u = load_data("teacher_unavailability.csv")
                new_row = pd.DataFrame([{"Teacher": w_t, "Day": w_d, "Reason": "Unavailable"}])
                df_u = pd.concat([df_u, new_row], ignore_index=True)
                save_data(df_u, "teacher_unavailability.csv")
                st.success(f"Added: {w_t} off on {w_d}")

        df_u = st.data_editor(load_data("teacher_unavailability.csv"), num_rows="dynamic", key="du", use_container_width=True)
        if st.button("💾 Save Constraints"): save_data(df_u, "teacher_unavailability.csv"); st.toast("Constraints Saved")

# --- TAB: GENERATOR ---
elif menu == "Generator":
    st.markdown('<div class="main-header">AI Engine</div>', unsafe_allow_html=True)
    
    col_main, col_logs = st.columns([2, 1])

    with col_main:
        st.markdown("""
        <div style="border:1px solid #334155; padding:20px; border-radius:10px; background:rgba(0,0,0,0.2);">
            <h4>🚀 Generate Timetables</h4>
            <p style="color:#94A3B8;">This utilizes Google OR-Tools (CP-SAT) to solve the scheduling constraint problem.</p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        if st.button("▶️ Start Computation", type="primary", use_container_width=True):
            if not BACKEND_AVAILABLE:
                st.error("❌ Logic scripts missing.")
            else:
                progress = st.progress(0)
                status = st.empty()
                
                try:
                    status.write("🔍 Validating Inputs...")
                    progress.progress(20)
                    data_validator.main()
                    
                    status.write("🧠 Optimizing Schedule (This may take a minute)...")
                    progress.progress(50)
                    solver_engine.run() # Ensure your main.py creates files in /output
                    
                    progress.progress(100)
                    status.write("✅ Done!")
                    st.balloons()
                except Exception as e:
                    status.error(f"Fatal Error: {e}")

    with col_logs:
        st.write("**Engine Logs**")
        if os.path.exists("warnings.log"):
            with open("warnings.log", "r") as f:
                st.code(f.read(), language="text")
        else:
            st.info("No warnings generated.")

# --- TAB: SCHEDULES ---
elif menu == "Schedules":
    st.markdown('<div class="main-header">Routine Hub</div>', unsafe_allow_html=True)

    if not os.path.exists("output") or not os.listdir("output"):
        st.info("No schedules found. Run the Generator first.")
    else:
        files = sorted([f for f in os.listdir("output") if f.endswith(".html")])
        
        c_sel, c_act = st.columns([3, 1])
        with c_sel:
            selected_file = st.selectbox("Select Timetable", files)
        with c_act:
            st.write("") # Spacer
            if st.button("🔄 Refresh"): st.rerun()

        if selected_file:
            path = os.path.join("output", selected_file)
            
            # 1. Get the High-Contrast HTML
            html_view = get_asc_styled_html(path)
            
            # 2. Render
            st.components.v1.html(html_view, height=800, scrolling=True)
            
            # 3. Download
            with open(path, "rb") as f:
                st.download_button(
                    "📥 Download HTML", 
                    f, 
                    file_name=selected_file, 
                    mime="text/html"
                )
