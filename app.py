import json
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Data layer (same JSON-backed storage as the original script)
# ----------------------------------------------------------------------------

DATABASE = "school_database.json"


def load_data():
    if Path(DATABASE).exists():
        with open(DATABASE, "r") as f:
            content = f.read()
            if content:
                return json.loads(content)
    return {"students": [], "teachers": []}


def save(data):
    with open(DATABASE, "w") as f:
        json.dump(data, f, indent=4)


if "data" not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data


# ----------------------------------------------------------------------------
# Domain classes (same abstractions, adapted to return results instead of
# printing / reading from stdin, so they can be driven by the UI)
# ----------------------------------------------------------------------------

class Person(ABC):
    @abstractmethod
    def get_role(self):
        pass

    @staticmethod
    def validate_email(email):
        return "@" in email and "." in email


class Student(Person):
    def get_role(self):
        return "Student"

    def register(self, name, age, email, roll_number):
        if not Person.validate_email(email):
            return False, "Invalid email format!"
        if not name or not roll_number:
            return False, "Name and roll number are required."
        for i in data["students"]:
            if i["roll_number"] == roll_number:
                return False, "A student with this roll number already exists!"
        data["students"].append({
            "name": name,
            "age": age,
            "email": email,
            "roll_number": roll_number,
            "grades": {},
        })
        save(data)
        return True, f"Student '{name}' registered successfully!"

    def find(self, roll_number):
        for i in data["students"]:
            if i["roll_number"] == roll_number:
                return i
        return None

    def add_grade(self, roll_number, subject, grade):
        student_record = self.find(roll_number)
        if not student_record:
            return False, "Student with this roll number does not exist!"
        if not subject:
            return False, "Subject is required."
        student_record["grades"][subject] = grade
        save(data)
        return True, "Grade added successfully!"


class Teacher(Person):
    def get_role(self):
        return "Teacher"

    def register(self, name, age, email, emp_id, subject):
        if not Person.validate_email(email):
            return False, "Invalid email format!"
        if not name or not emp_id:
            return False, "Name and employee ID are required."
        for i in data["teachers"]:
            if i["emp_id"] == emp_id:
                return False, "A teacher with this employee ID already exists!"
        data["teachers"].append({
            "name": name,
            "age": age,
            "email": email,
            "emp_id": emp_id,
            "subject": subject,
        })
        save(data)
        return True, f"Teacher '{name}' registered successfully!"

    def find(self, emp_id):
        for i in data["teachers"]:
            if i["emp_id"] == emp_id:
                return i
        return None


stud = Student()
teach = Teacher()


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------

st.set_page_config(
    page_title="School Management System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Global color grade + 3D animation styles --------------------------------
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

        html, body, [class*="css"]  { font-family: 'Poppins', sans-serif; }

        .stApp {
            background: radial-gradient(circle at 15% 10%, #2b1055 0%, #0f0c29 45%, #060612 100%);
            background-attachment: fixed;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a0f3d 0%, #10082a 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
        }

        h1, h2, h3 {
            background: linear-gradient(90deg, #ff6ec4, #7873f5, #4adede);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 800 !important;
        }

        /* Metric cards -> glass + glow */
        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 8px 24px rgba(120,115,245,0.15), inset 0 1px 0 rgba(255,255,255,0.08);
            backdrop-filter: blur(6px);
        }

        /* Forms -> glass card w/ subtle 3D tilt on hover */
        div[data-testid="stForm"] {
            background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 12px 32px rgba(0,0,0,0.35);
            transform-style: preserve-3d;
            perspective: 800px;
            transition: transform 0.35s ease, box-shadow 0.35s ease;
        }
        div[data-testid="stForm"]:hover {
            transform: rotateX(1.5deg) rotateY(-1.5deg) translateY(-2px);
            box-shadow: 0 20px 45px rgba(120,115,245,0.28);
        }

        .stButton>button, .stFormSubmitButton>button {
            background: linear-gradient(90deg, #ff6ec4, #7873f5);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 700;
            letter-spacing: 0.3px;
            box-shadow: 0 6px 18px rgba(120,115,245,0.4);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .stButton>button:hover, .stFormSubmitButton>button:hover {
            transform: translateY(-2px) scale(1.02);
            box-shadow: 0 10px 26px rgba(255,110,196,0.45);
        }

        .stTabs [data-baseweb="tab-list"] { gap: 6px; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            padding: 8px 18px;
            background: rgba(255,255,255,0.04);
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, rgba(255,110,196,0.25), rgba(120,115,245,0.25)) !important;
        }

        [data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }

        /* ---------------- Bin + 3D animations ---------------- */

        .bin-anchor {
            position: fixed;
            bottom: 28px;
            right: 34px;
            font-size: 46px;
            z-index: 999;
            filter: drop-shadow(0 8px 16px rgba(120,115,245,0.45));
            animation: binIdle 3s ease-in-out infinite;
            perspective: 600px;
        }
        @keyframes binIdle {
            0%, 100% { transform: translateY(0) rotateZ(0deg); }
            50% { transform: translateY(-4px) rotateZ(-3deg); }
        }
        .bin-anchor.bin-open {
            animation: binOpen 0.9s ease;
        }
        @keyframes binOpen {
            0%   { transform: scale(1) rotateZ(0deg); }
            30%  { transform: scale(1.25) rotateZ(-12deg); }
            55%  { transform: scale(1.3) rotateZ(10deg); }
            100% { transform: scale(1) rotateZ(0deg); }
        }

        /* Card that "flies" into the bin after a successful add */
        .fly-to-bin-wrap { perspective: 1000px; }
        .fly-to-bin {
            transform-origin: bottom right;
            animation: flyToBin 1.1s cubic-bezier(.55,.06,.68,.19) forwards;
        }
        @keyframes flyToBin {
            0%   { transform: translate(0,0) scale(1) rotate(0deg) rotateY(0deg); opacity: 1; }
            60%  { transform: translate(40vw, 25vh) scale(0.55) rotate(25deg) rotateY(180deg); opacity: 0.9; }
            100% { transform: translate(78vw, 60vh) scale(0.05) rotate(70deg) rotateY(540deg); opacity: 0; }
        }

        /* Detail card that "pops out" of the bin, 3D flip reveal */
        .pop-from-bin-wrap { perspective: 1200px; }
        .pop-from-bin {
            transform-origin: bottom right;
            animation: popFromBin 0.85s cubic-bezier(.34,1.56,.64,1) both;
        }
        @keyframes popFromBin {
            0%   { transform: translate(70vw, 55vh) scale(0.05) rotate(-60deg) rotateY(-400deg); opacity: 0; }
            60%  { transform: translate(-2vw, -1vh) scale(1.06) rotate(3deg) rotateY(15deg); opacity: 1; }
            100% { transform: translate(0,0) scale(1) rotate(0deg) rotateY(0deg); opacity: 1; }
        }

        .glass-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 18px;
            padding: 22px 26px;
            box-shadow: 0 16px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08);
            margin-bottom: 14px;
        }
        .glass-card h3 { margin-top: 0; }
        .pill {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            background: linear-gradient(90deg, #4adede, #7873f5);
            color: #060612;
            margin-right: 6px;
        }
        .success-toast {
            background: linear-gradient(145deg, rgba(74,222,128,0.18), rgba(74,222,128,0.05));
            border: 1px solid rgba(74,222,128,0.4);
            border-radius: 14px;
            padding: 14px 18px;
            font-weight: 600;
            color: #b8f6c9;
        }
        .error-toast {
            background: linear-gradient(145deg, rgba(255,110,110,0.18), rgba(255,110,110,0.05));
            border: 1px solid rgba(255,110,110,0.4);
            border-radius: 14px;
            padding: 14px 18px;
            font-weight: 600;
            color: #ffc2c2;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Server-side trigger for the bin "open" bounce. Streamlit reruns the whole
# script on every interaction, so a plain module-level flag set during this
# run is enough to decide, at the bottom of the script, whether the bin
# should play its open animation for the render that just happened.
_bin_should_open = False


def fly_to_bin(message: str):
    """Render a success message that visually flies off into the bin icon."""
    global _bin_should_open
    _bin_should_open = True
    st.markdown(
        f"""
        <div class="fly-to-bin-wrap">
            <div class="glass-card success-toast fly-to-bin">✅ {message} &nbsp;→&nbsp; filed away 🗑️</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mark_bin_open():
    global _bin_should_open
    _bin_should_open = True


def error_toast(message: str):
    st.markdown(f'<div class="glass-card error-toast">⚠️ {message}</div>', unsafe_allow_html=True)


def render_bin():
    bin_class = "bin-anchor bin-open" if _bin_should_open else "bin-anchor"
    st.markdown(f'<div class="{bin_class}">🗑️</div>', unsafe_allow_html=True)


with st.sidebar:
    st.markdown("## 🎓 School Manager")
    st.caption("Students · Teachers · Grades")
    page = st.radio(
        "Navigate",
        [
            "📊 Dashboard",
            "🧑‍🎓 Register Student",
            "🧑‍🏫 Register Teacher",
            "📝 Add Grade",
            "🔍 Student Lookup",
            "🔍 Teacher Lookup",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(f"Data file: `{DATABASE}`")
    st.caption(f"Students: {len(data['students'])}  |  Teachers: {len(data['teachers'])}")


def avg_grade(student_record):
    grades = student_record.get("grades", {})
    return sum(grades.values()) / len(grades) if grades else 0.0


# ---- Dashboard --------------------------------------------------------------
if page == "📊 Dashboard":
    st.title("📊 Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Students", len(data["students"]))
    col2.metric("Total Teachers", len(data["teachers"]))
    all_avgs = [avg_grade(s) for s in data["students"] if s.get("grades")]
    col3.metric("Overall Avg. Grade", f"{(sum(all_avgs)/len(all_avgs)):.1f}" if all_avgs else "—")

    st.divider()

    tab1, tab2 = st.tabs(["Students", "Teachers"])

    with tab1:
        if data["students"]:
            df = pd.DataFrame([
                {
                    "Name": s["name"],
                    "Age": s["age"],
                    "Email": s["email"],
                    "Roll No.": s["roll_number"],
                    "Subjects": len(s.get("grades", {})),
                    "Avg. Grade": round(avg_grade(s), 2) if s.get("grades") else None,
                }
                for s in data["students"]
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No students registered yet.")

    with tab2:
        if data["teachers"]:
            df = pd.DataFrame([
                {
                    "Name": t["name"],
                    "Age": t["age"],
                    "Email": t["email"],
                    "Employee ID": t["emp_id"],
                    "Subject": t["subject"],
                }
                for t in data["teachers"]
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No teachers registered yet.")

# ---- Register Student --------------------------------------------------------
elif page == "🧑‍🎓 Register Student":
    st.title("🧑‍🎓 Register Student")
    with st.form("register_student", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name")
        age = c2.number_input("Age", min_value=3, max_value=100, step=1, value=15)
        email = c1.text_input("Email")
        roll_number = c2.text_input("Roll number")
        submitted = st.form_submit_button("Register Student", use_container_width=True)

    if submitted:
        ok, message = stud.register(name.strip(), int(age), email.strip(), roll_number.strip())
        fly_to_bin(message) if ok else error_toast(message)

# ---- Register Teacher --------------------------------------------------------
elif page == "🧑‍🏫 Register Teacher":
    st.title("🧑‍🏫 Register Teacher")
    with st.form("register_teacher", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name")
        age = c2.number_input("Age", min_value=18, max_value=100, step=1, value=30)
        email = c1.text_input("Email")
        emp_id = c2.text_input("Employee ID")
        subject = st.text_input("Subject taught")
        submitted = st.form_submit_button("Register Teacher", use_container_width=True)

    if submitted:
        ok, message = teach.register(name.strip(), int(age), email.strip(), emp_id.strip(), subject.strip())
        fly_to_bin(message) if ok else error_toast(message)

# ---- Add Grade ----------------------------------------------------------------
elif page == "📝 Add Grade":
    st.title("📝 Add Grade")

    if not data["students"]:
        st.info("Register a student first before adding grades.")
    else:
        roll_lookup = {f'{s["name"]} ({s["roll_number"]})': s["roll_number"] for s in data["students"]}
        with st.form("add_grade", clear_on_submit=True):
            selection = st.selectbox("Student", list(roll_lookup.keys()))
            c1, c2 = st.columns(2)
            subject = c1.text_input("Subject")
            grade = c2.number_input("Grade", min_value=0.0, max_value=100.0, step=0.5, value=75.0)
            submitted = st.form_submit_button("Add Grade", use_container_width=True)

        if submitted:
            roll_number = roll_lookup[selection]
            ok, message = stud.add_grade(roll_number, subject.strip(), float(grade))
            fly_to_bin(message) if ok else error_toast(message)

# ---- Student Lookup -------------------------------------------------------------
elif page == "🔍 Student Lookup":
    st.title("🔍 Student Lookup")

    if not data["students"]:
        st.info("No students registered yet.")
    else:
        roll_lookup = {f'{s["name"]} ({s["roll_number"]})': s["roll_number"] for s in data["students"]}
        selection = st.selectbox("Select a student", list(roll_lookup.keys()))
        record = stud.find(roll_lookup[selection])

        if record:
            grades_html = "".join(
                f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                f'border-bottom:1px solid rgba(255,255,255,0.08);">'
                f'<span>{k}</span><span style="font-weight:700;">{v}</span></div>'
                for k, v in record["grades"].items()
            ) or '<span style="opacity:0.6;">No grades recorded yet.</span>'

            st.markdown(
                f"""
                <div class="pop-from-bin-wrap">
                  <div class="glass-card pop-from-bin">
                    <h3>📤 {record['name']}</h3>
                    <span class="pill">Roll {record['roll_number']}</span>
                    <span class="pill">Age {record['age']}</span>
                    <span class="pill">Avg {avg_grade(record):.1f}</span>
                    <p style="opacity:0.75; margin-top:10px;">✉️ {record['email']}</p>
                    <hr style="border-color: rgba(255,255,255,0.1);">
                    <h4 style="-webkit-text-fill-color:#e6e6ff; background:none;">Grades</h4>
                    {grades_html}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            mark_bin_open()

            if record["grades"]:
                gdf = pd.DataFrame(
                    [{"Subject": k, "Grade": v} for k, v in record["grades"].items()]
                )
                st.bar_chart(gdf.set_index("Subject"))

# ---- Teacher Lookup ---------------------------------------------------------------
elif page == "🔍 Teacher Lookup":
    st.title("🔍 Teacher Lookup")

    if not data["teachers"]:
        st.info("No teachers registered yet.")
    else:
        id_lookup = {f'{t["name"]} ({t["emp_id"]})': t["emp_id"] for t in data["teachers"]}
        selection = st.selectbox("Select a teacher", list(id_lookup.keys()))
        record = teach.find(id_lookup[selection])

        if record:
            st.markdown(
                f"""
                <div class="pop-from-bin-wrap">
                  <div class="glass-card pop-from-bin">
                    <h3>📤 {record['name']}</h3>
                    <span class="pill">ID {record['emp_id']}</span>
                    <span class="pill">Age {record['age']}</span>
                    <span class="pill">{record['subject']}</span>
                    <p style="opacity:0.75; margin-top:10px;">✉️ {record['email']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            mark_bin_open()

# ---- Always render the bin last so it sits on top with the correct state ----
render_bin()