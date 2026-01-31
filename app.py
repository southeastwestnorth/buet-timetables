import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components
import main  # Logic script
import data_validator # Validator script
import hashlib
from bs4 import BeautifulSoup

# --- CONFIG ---
st.set_page_config(page_title="Cadence", page_icon="🎓", layout="wide")

# --- LIGHT & BEAUTIFUL UI STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F8FAFC; }

    /* Modern Dashboard Headers */
    .main-header { font-size: 2.2rem; font-weight: 800; color: #1E293B; letter-spacing: -0.03em; margin-bottom: 5px; }
    .sub-header { font-size: 1rem; color: #64748B; margin-bottom: 25px; }

    /* Minimal Metric Cards */
    .metric-container {
        background: white; padding: 20px; border-radius: 12px;
        border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .m-label { color: #94A3B8; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }
    .m-value { font-size: 1.6rem; font-weight: 800; color: #334155; }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; background-color: white; border-radius: 8px 8px 0 0;
        border: 1px solid #E2E8F0; padding: 10px 20px; font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background-color: #3B82F6 !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- aSc STYLE INJECTION ENGINE ---
def get_asc_styled_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_html = f.read()

    # aSc Table CSS
    asc_css = """
    <style>
        table {
            width: 100%; border-collapse: separate; border-spacing: 4px;
            font-family: 'Inter', sans-serif; table-layout: fixed;
        }
        th {
            background-color: #F1F5F9; color: #475569; font-weight: 700;
            padding: 12px; font-size: 12px; border-radius: 6px;
        }
        td {
            height: 85px; vertical-align: top; padding: 8px; border-radius: 6px;
            border: 1px solid #E2E8F0; transition: 0.2s; position: relative;
            background-color: #FFFFFF;
        }
        .day-cell { background-color: #475569 !important; color: white !important; font-weight: 700; width: 60px; text-align: center; vertical-align: middle; }

        /* Lesson content styling */
        .cell-wrap { display: flex; flex-direction: column; height: 100%; }
        .subject { font-weight: 800; font-size: 13px; color: #1E293B; line-height: 1.2; margin-bottom: auto; }
        .details-row { display: flex; justify-content: space-between; align-items: flex-end; margin-top: 5px; }
        .teacher { font-size: 10px; color: #64748B; font-weight: 500; }
        .room { font-size: 10px; color: #3B82F6; font-weight: 700; background: #EFF6FF; padding: 1px 4px; border-radius: 3px; }
    </style>
    """

    # Consistent Color Logic
    def get_subject_color(name):
        h = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360
        return f"hsla({h}, 75%, 92%, 1)"

    soup = BeautifulSoup(raw_html, "html.parser")

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells: continue

        # Mark the first column as day headers
        cells[0]['class'] = 'day-cell'

        for cell in cells[1:]:
            # Use BeautifulSoup to find elements instead of regex on text
            subj_tag = cell.find("span", class_="subject-id")
            teacher_tag = cell.find("div", class_="teacher-id")
            room_tag = cell.find("div", class_="room-info")

            if subj_tag:
                subj = subj_tag.get_text(strip=True)
                teacher = teacher_tag.get_text(strip=True) if teacher_tag else ""
                room = room_tag.get_text(strip=True) if room_tag else ""

                color = get_subject_color(subj)
                cell['style'] = f"background-color: {color};"

                new_content = f"""
                <div class="cell-wrap">
                    <div class="subject">{subj}</div>
                    <div class="details-row">
                        <div class="teacher">{teacher}</div>
                        <div class="room">{room}</div>
                    </div>
                </div>
                """
                # Clear existing contents and inject new structure
                cell.clear()
                cell.append(BeautifulSoup(new_content, "html.parser"))

    return asc_css + str(soup)

# --- UTILS ---
def load(name):
    p = f"data/{name}"
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

def save(df, name):
    df.to_csv(f"data/{name}", index=False)

# --- UI ---
menu = st.sidebar.radio("Navigation", ["Overview", "Data Studio", "Generator", "Schedules"])

if menu == "Overview":
    st.markdown('<div class="main-header">Department Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Summary of academic resources</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    # Using specific counts from loaded data
    teachers_count = len(load("teachers.csv"))
    classes_count = len(load("classes.csv"))
    rooms_count = len(load("rooms.csv"))
    load_count = len(load("curriculum.csv"))

    with c1: st.markdown(f'<div class="metric-container"><div class="m-label">Teachers</div><div class="m-value">{teachers_count}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-container"><div class="m-label">Classes</div><div class="m-value">{classes_count}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-container"><div class="m-label">Rooms</div><div class="m-value">{rooms_count}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-container"><div class="m-label">Load</div><div class="m-value">{load_count}</div></div>', unsafe_allow_html=True)

    st.divider()
    st.info("💡 Start by verifying your data in **Data Studio**, then execute the **Generator**.")

elif menu == "Data Studio":
    st.markdown('<div class="main-header">Data Studio</div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Infrastructure", "Curriculum", "Constraints"])

    with t1:
        st.write("**Teachers**")
        df_t = st.data_editor(load("teachers.csv"), num_rows="dynamic", key="dt", width='stretch')
        if st.button("💾 Save Teachers"):
            save(df_t, "teachers.csv"); st.toast("Teachers Saved!")

        st.write("**Rooms**")
        df_r = st.data_editor(load("rooms.csv"), num_rows="dynamic", key="dr", width='stretch')
        if st.button("💾 Save Rooms"):
            save(df_r, "rooms.csv"); st.toast("Rooms Saved!")

        st.write("**Classes**")
        df_cls = st.data_editor(load("classes.csv"), num_rows="dynamic", key="dcls", width='stretch')
        if st.button("💾 Save Classes"):
            save(df_cls, "classes.csv"); st.toast("Classes Saved!")

        st.write("**Subjects**")
        df_sub = st.data_editor(load("subjects.csv"), num_rows="dynamic", key="dsub", width='stretch')
        if st.button("💾 Save Subjects"):
            save(df_sub, "subjects.csv"); st.toast("Subjects Saved!")

        st.write("**Timeslots**")
        df_ts = st.data_editor(load("timeslots.csv"), num_rows="dynamic", key="dts", width='stretch')
        if st.button("💾 Save Timeslots"):
            save(df_ts, "timeslots.csv"); st.toast("Timeslots Saved!")

    with t2:
        st.write("**Assignments**")
        df_c = st.data_editor(load("curriculum.csv"), num_rows="dynamic", key="dc", width='stretch')
        if st.button("💾 Save Curriculum"):
            save(df_c, "curriculum.csv"); st.toast("Curriculum Saved!")

    with t3:
        st.write("**Teacher Unavailability**")
        df_u = st.data_editor(load("teacher_unavailability.csv"), num_rows="dynamic", key="du", width='stretch')
        if st.button("💾 Save Unavailability"):
            save(df_u, "teacher_unavailability.csv"); st.toast("Unavailability Saved!")

        st.write("**Teacher Preferences**")
        df_p = st.data_editor(load("teacher_preferences.csv"), num_rows="dynamic", key="dp", width='stretch')
        if st.button("💾 Save Preferences"):
            save(df_p, "teacher_preferences.csv"); st.toast("Preferences Saved!")

elif menu == "Generator":
    st.markdown('<div class="main-header">AI Generator</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.write("Click below to run the Google OR-Tools solver. It will find the most efficient schedule based on your constraints.")
        if st.button("🚀 Run Scheduler", type="primary", width='stretch'):
            with st.status("Engine is calculating...") as s:
                st.write("Validating data...")
                data_validator.main()
                st.write("Generating routine...")
                res = main.run()
                s.update(label="Routine Generated!", state="complete")
            st.balloons()

            # Show warnings.log if it exists and has content
            if os.path.exists("warnings.log"):
                with open("warnings.log", "r") as f:
                    warnings = f.read()
                if warnings:
                    with st.expander("⚠️ Data Validation Report", expanded=True):
                        st.code(warnings)

elif menu == "Schedules":
    st.markdown('<div class="main-header">Routine Hub</div>', unsafe_allow_html=True)
    if os.path.exists("output"):
        files = [f for f in os.listdir("output") if f.endswith(".html")]
        if files:
            target = st.selectbox("Select Target Timetable", sorted(files))
            styled_html = get_asc_styled_html(f"output/{target}")

            # Display high-quality table
            st.container(border=True).markdown('<div style="background:white; padding:10px; border-radius:8px;">', unsafe_allow_html=True)
            components.html(styled_html, height=700, scrolling=True)

            st.download_button("📥 Export HTML", styled_html, file_name=target, mime="text/html")
        else:
            st.info("No routine files found. Please run the generator.")
