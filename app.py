import streamlit as st
import pandas as pd
import os
import glob
import streamlit.components.v1 as components
import main  # Imports your friend's logic

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Uni-Scheduler Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR "PRO" LOOK ---
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1E3A8A; font-weight: 700;}
    .sub-header {font-size: 1.5rem; color: #4B5563;}
    .card {
        background-color: #f9fafb;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .big-number {font-size: 2rem; font-weight: bold; color: #2563EB;}
    .stButton>button {width: 100%; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2997/2997287.png", width=80)
    st.title("Timetable Admin")
    menu = st.radio("Navigate", ["📊 Dashboard", "📝 Manage Data", "⚙️ Generator", "📅 View Schedules"])
    
    st.divider()
    st.info("System Status: Ready")
    st.caption("v1.0 | Powered by OR-Tools")

# --- HELPER FUNCTIONS ---
def load_csv(filename):
    path = os.path.join("data", filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def save_csv(df, filename):
    path = os.path.join("data", filename)
    df.to_csv(path, index=False)

def count_rows(filename):
    df = load_csv(filename)
    return len(df)

# --- MAIN SECTIONS ---

if menu == "📊 Dashboard":
    st.markdown('<p class="main-header">University Scheduler Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Overview of current academic resources</p>', unsafe_allow_html=True)
    
    # Metrics Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="card">Teachers<div class="big-number">{count_rows("teachers.csv")}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card">Classes<div class="big-number">{count_rows("classes.csv")}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="card">Rooms<div class="big-number">{count_rows("rooms.csv")}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="card">Curriculum Entries<div class="big-number">{count_rows("curriculum.csv")}</div></div>', unsafe_allow_html=True)

    st.divider()
    st.write("### 📌 Quick Actions")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Go to Generator", type="primary"):
            st.warning("Please switch to the 'Generator' tab using the sidebar.")
    with col_b:
        st.info("💡 Tip: Ensure your 'Curriculum' matches your 'Timeslots' before running.")

elif menu == "📝 Manage Data":
    st.markdown('<p class="main-header">Data Management</p>', unsafe_allow_html=True)
    
    # Categorize the files for better UX
    tabs = st.tabs(["🏫 Resources", "📚 Academic", "⚠️ Constraints", "🔗 Curriculum"])
    
    with tabs[0]: # Resources
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Teachers")
            df_t = load_csv("teachers.csv")
            edit_t = st.data_editor(df_t, num_rows="dynamic", key="edit_teachers", use_container_width=True)
            if st.button("Save Teachers"):
                save_csv(edit_t, "teachers.csv")
                st.success("Teachers updated!")
        with c2:
            st.subheader("Rooms")
            df_r = load_csv("rooms.csv")
            edit_r = st.data_editor(df_r, num_rows="dynamic", key="edit_rooms", use_container_width=True)
            if st.button("Save Rooms"):
                save_csv(edit_r, "rooms.csv")
                st.success("Rooms updated!")

    with tabs[1]: # Academic
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Classes (Sections)")
            df_c = load_csv("classes.csv")
            edit_c = st.data_editor(df_c, num_rows="dynamic", key="edit_classes", use_container_width=True)
            if st.button("Save Classes"):
                save_csv(edit_c, "classes.csv")
                st.success("Classes updated!")
        with c2:
            st.subheader("Subjects")
            df_s = load_csv("subjects.csv")
            edit_s = st.data_editor(df_s, num_rows="dynamic", key="edit_subjects", use_container_width=True)
            if st.button("Save Subjects"):
                save_csv(edit_s, "subjects.csv")
                st.success("Subjects updated!")

    with tabs[2]: # Constraints
        st.subheader("Teacher Unavailability")
        st.caption("Define when teachers CANNOT work. (Day 1 = Monday, Period 1 = First slot)")
        df_u = load_csv("teacher_unavailability.csv")
        edit_u = st.data_editor(df_u, num_rows="dynamic", key="edit_unavail", use_container_width=True)
        if st.button("Save Unavailability"):
            save_csv(edit_u, "teacher_unavailability.csv")
            st.success("Constraints updated!")
            
        st.divider()
        st.subheader("Teacher Preferences")
        st.caption("Define when teachers PREFER to work (Soft constraint).")
        df_p = load_csv("teacher_preferences.csv")
        edit_p = st.data_editor(df_p, num_rows="dynamic", key="edit_prefs", use_container_width=True)
        if st.button("Save Preferences"):
            save_csv(edit_p, "teacher_preferences.csv")
            st.success("Preferences updated!")

    with tabs[3]: # Curriculum
        st.subheader("Master Curriculum")
        st.markdown("**This is the most important table.** It links Classes + Subjects + Teachers.")
        df_curr = load_csv("curriculum.csv")
        edit_curr = st.data_editor(df_curr, num_rows="dynamic", key="edit_curr", use_container_width=True)
        if st.button("Save Curriculum"):
            save_csv(edit_curr, "curriculum.csv")
            st.success("Curriculum Saved!")

elif menu == "⚙️ Generator":
    st.markdown('<p class="main-header">Schedule Generator</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        The AI Solver uses **Google OR-Tools** to find the optimal schedule. 
        It considers:
        * Teacher availability & Load
        * Room capacities
        * Non-overlapping classes
        """)
    with col2:
        st.metric(label="Time Limit (Seconds)", value="30s")

    st.divider()
    
    if st.button("🚀 Run Scheduler Algorithm", type="primary", use_container_width=True):
        status_box = st.empty()
        status_box.info("Initializing solver...")
        
        try:
            # RUN THE BACKEND SCRIPT
            result = main.run()
            
            if "SUCCESS" in result['status']:
                status_box.success("🎉 Optimization Successful! Timetables generated.")
                st.balloons()
                
                # Show results summary
                r1, r2 = st.columns(2)
                r1.metric("Total Sessions Required", result['sessions_total'])
                r2.metric("Sessions Successfully Scheduled", result['sessions_scheduled'])
                
                if result['sessions_total'] != result['sessions_scheduled']:
                    st.warning("⚠️ Some sessions could not be scheduled due to conflicts. Check 'all_assignments.csv'.")
            else:
                status_box.error("❌ " + result['status'])
                
        except Exception as e:
            st.error(f"An critical error occurred: {e}")

elif menu == "📅 View Schedules":
    st.markdown('<p class="main-header">Timetable Viewer</p>', unsafe_allow_html=True)
    
    output_dir = "output"
    if not os.path.exists(output_dir):
        st.error("Output directory missing. Run the generator first.")
    else:
        # Separate files by type
        all_files = os.listdir(output_dir)
        class_files = [f for f in all_files if f.startswith("class_") and f.endswith(".html")]
        teacher_files = [f for f in all_files if f.startswith("teacher_") and f.endswith(".html")]
        
        # Filter Toggle
        view_type = st.radio("View Mode", ["Student/Class View", "Teacher View"], horizontal=True)
        
        selected_file = None
        if view_type == "Student/Class View":
            if class_files:
                choice = st.selectbox("Select Class", class_files, format_func=lambda x: x.replace("class_", "").replace("_timetable.html", ""))
                selected_file = choice
            else:
                st.warning("No class timetables found.")
                
        else:
            if teacher_files:
                choice = st.selectbox("Select Teacher", teacher_files, format_func=lambda x: x.replace("teacher_", "").replace("_timetable.html", ""))
                selected_file = choice
            else:
                st.warning("No teacher timetables found.")

        # Render the HTML
        if selected_file:
            path = os.path.join(output_dir, selected_file)
            with open(path, 'r', encoding='utf-8') as f:
                html_code = f.read()
                
            st.markdown("### Preview")
            components.html(html_code, height=600, scrolling=True)
            
            st.download_button("📥 Download This Schedule", html_code, file_name=selected_file, mime="text/html")
