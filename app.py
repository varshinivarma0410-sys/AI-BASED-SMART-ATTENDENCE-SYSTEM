import streamlit as st
import sqlite3
import pandas as pd
import cv2
import os
import numpy as np
import face_recognition
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Smart Attendance System",
    page_icon="📋",
    layout="wide"
)

DB_PATH = "data/attendance.db"
FACES_DIR = "faces"

os.makedirs("data", exist_ok=True)
os.makedirs(FACES_DIR, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            time TEXT,
            status TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    conn.commit()
    conn.close()


initialize_database()


# ============================================================
# STUDENT FUNCTIONS
# ============================================================

def get_students():

    conn = get_connection()

    query = """
        SELECT id, name, roll_number
        FROM students
        ORDER BY id
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


def register_student(name, roll_number, image):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "SELECT id FROM students WHERE roll_number = ?",
            (roll_number,)
        )

        existing = cursor.fetchone()

        if existing:
            conn.close()
            return False, "Roll number already exists."

        # Check that the image contains a face
        rgb_image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        face_locations = face_recognition.face_locations(
            rgb_image
        )

        if len(face_locations) == 0:

            conn.close()

            return False, "No face detected. Please capture a clear face."

        if len(face_locations) > 1:

            conn.close()

            return False, "Multiple faces detected. Please capture only one person."

        cursor.execute("""
            INSERT INTO students
            (name, roll_number)
            VALUES (?, ?)
        """, (name, roll_number))

        student_id = cursor.lastrowid

        conn.commit()
        conn.close()

        image_path = os.path.join(
            FACES_DIR,
            f"{roll_number}.jpg"
        )

        cv2.imwrite(
            image_path,
            image
        )

        return True, (
            f"Student registered successfully. "
            f"Student ID: {student_id}"
        )

    except Exception as e:

        conn.rollback()
        conn.close()

        return False, str(e)


# ============================================================
# ATTENDANCE FUNCTIONS
# ============================================================

def mark_attendance(student_id):

    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    cursor.execute("""
        SELECT id
        FROM attendance
        WHERE student_id = ?
        AND date = ?
    """, (
        student_id,
        today
    ))

    existing = cursor.fetchone()

    if existing:

        conn.close()

        return False, "Attendance already marked for today."

    cursor.execute("""
        INSERT INTO attendance
        (student_id, date, time, status)
        VALUES (?, ?, ?, ?)
    """, (
        student_id,
        today,
        current_time,
        "Present"
    ))

    conn.commit()
    conn.close()

    return True, "Attendance marked successfully."


def get_attendance():

    conn = get_connection()

    query = """
        SELECT
            attendance.id AS ID,
            students.name AS Name,
            students.roll_number AS Roll_Number,
            attendance.date AS Date,
            attendance.time AS Time,
            attendance.status AS Status
        FROM attendance
        LEFT JOIN students
        ON attendance.student_id = students.id
        ORDER BY attendance.date DESC,
                 attendance.time DESC
    """

    df = pd.read_sql_query(
        query,
        conn
    )

    conn.close()

    return df


# ============================================================
# FACE RECOGNITION
# ============================================================

def load_known_faces():

    known_face_encodings = []
    known_face_names = []
    known_student_ids = []

    students_df = get_students()

    for _, student in students_df.iterrows():

        roll_number = str(
            student["roll_number"]
        )

        image_path = os.path.join(
            FACES_DIR,
            f"{roll_number}.jpg"
        )

        if not os.path.exists(image_path):
            continue

        try:

            image = face_recognition.load_image_file(
                image_path
            )

            encodings = face_recognition.face_encodings(
                image
            )

            if len(encodings) == 0:
                continue

            known_face_encodings.append(
                encodings[0]
            )

            known_face_names.append(
                student["name"]
            )

            known_student_ids.append(
                int(student["id"])
            )

        except Exception:
            continue

    return (
        known_face_encodings,
        known_face_names,
        known_student_ids
    )


def recognize_face(image):

    (
        known_face_encodings,
        known_face_names,
        known_student_ids
    ) = load_known_faces()

    if len(known_face_encodings) == 0:

        return None, None, "No registered face images found."

    rgb_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )

    face_locations = face_recognition.face_locations(
        rgb_image
    )

    if len(face_locations) == 0:

        return None, None, "No face detected."

    if len(face_locations) > 1:

        return None, None, "Multiple faces detected."

    face_encodings = face_recognition.face_encodings(
        rgb_image,
        face_locations
    )

    if len(face_encodings) == 0:

        return None, None, "Could not encode the face."

    current_encoding = face_encodings[0]

    distances = face_recognition.face_distance(
        known_face_encodings,
        current_encoding
    )

    best_match_index = np.argmin(
        distances
    )

    best_distance = distances[
        best_match_index
    ]

    # Recognition threshold
    tolerance = 0.50

    if best_distance <= tolerance:

        name = known_face_names[
            best_match_index
        ]

        student_id = known_student_ids[
            best_match_index
        ]

        return (
            name,
            student_id,
            "Face recognized"
        )

    return (
        None,
        None,
        "Face not recognized."
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📋 Smart Attendance")

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Select Page",
    [
        "Attendance Dashboard",
        "Register Student",
        "Automatic Face Attendance"
    ]
)

st.sidebar.markdown("---")

st.sidebar.info(
    "Smart Attendance System\n\n"
    "Python + Streamlit + SQLite + OpenCV + Face Recognition"
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "Attendance Dashboard":

    st.title("📊 Smart Attendance Dashboard")

    st.write(
        "View student attendance records and statistics."
    )

    st.markdown("---")

    attendance_df = get_attendance()
    students_df = get_students()

    total_students = len(
        students_df
    )

    total_attendance = len(
        attendance_df
    )

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    today_attendance = len(
        attendance_df[
            attendance_df["Date"] == today
        ]
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Total Students",
            total_students
        )

    with col2:

        st.metric(
            "Total Attendance",
            total_attendance
        )

    with col3:

        st.metric(
            "Today's Attendance",
            today_attendance
        )

    st.markdown("---")

    st.subheader("📋 Attendance Records")

    if attendance_df.empty:

        st.info(
            "No attendance records found."
        )

    else:

        st.dataframe(
            attendance_df,
            width="stretch",
            hide_index=True
        )

        csv_data = attendance_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download Attendance CSV",
            data=csv_data,
            file_name="attendance.csv",
            mime="text/csv",
            width="stretch"
        )

    st.markdown("---")

    st.subheader("👨‍🎓 Registered Students")

    if students_df.empty:

        st.info(
            "No students registered yet."
        )

    else:

        st.dataframe(
            students_df,
            width="stretch",
            hide_index=True
        )


# ============================================================
# REGISTER STUDENT
# ============================================================

elif page == "Register Student":

    st.title("👨‍🎓 Register Student")

    st.write(
        "Register a student and capture their face."
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Student Details")

        name = st.text_input(
            "Student Name",
            placeholder="Enter student name"
        )

        roll_number = st.text_input(
            "Roll Number",
            placeholder="Enter roll number"
        )

    with col2:

        st.subheader("Face Capture")

        camera_image = st.camera_input(
            "Take a picture of the student"
        )

    st.markdown("---")

    if st.button(
        "Register Student",
        type="primary"
    ):

        if not name.strip():

            st.error(
                "Please enter the student name."
            )

        elif not roll_number.strip():

            st.error(
                "Please enter the roll number."
            )

        elif camera_image is None:

            st.error(
                "Please capture the student's face."
            )

        else:

            file_bytes = camera_image.getvalue()

            image_array = cv2.imdecode(
                np.frombuffer(
                    file_bytes,
                    dtype=np.uint8
                ),
                cv2.IMREAD_COLOR
            )

            if image_array is None:

                st.error(
                    "Unable to process the image."
                )

            else:

                success, message = register_student(
                    name.strip(),
                    roll_number.strip(),
                    image_array
                )

                if success:

                    st.success(message)

                    st.image(
                        camera_image,
                        caption="Registered Face",
                        width=300
                    )

                else:

                    st.error(message)


# ============================================================
# AUTOMATIC FACE ATTENDANCE
# ============================================================

elif page == "Automatic Face Attendance":

    st.title("🤖 Automatic Face Attendance")

    st.write(
        "Capture your face and the system will "
        "automatically identify the registered student."
    )

    st.markdown("---")

    camera_image = st.camera_input(
        "Look at the camera and capture your face"
    )

    if camera_image is not None:

        file_bytes = camera_image.getvalue()

        image_array = cv2.imdecode(
            np.frombuffer(
                file_bytes,
                dtype=np.uint8
            ),
            cv2.IMREAD_COLOR
        )

        if image_array is None:

            st.error(
                "Unable to process the camera image."
            )

        else:

            with st.spinner(
                "Recognizing face..."
            ):

                name, student_id, message = recognize_face(
                    image_array
                )

            if name is not None:

                st.success(
                    f"👤 Recognized: {name}"
                )

                attendance_success, attendance_message = (
                    mark_attendance(student_id)
                )

                if attendance_success:

                    st.success(
                        f"✅ {attendance_message}"
                    )

                    st.info(
                        f"Student: {name}"
                    )

                    st.info(
                        f"Time: "
                        f"{datetime.now().strftime('%H:%M:%S')}"
                    )

                else:

                    st.warning(
                        f"⚠️ {attendance_message}"
                    )

            else:

                st.error(
                    f"❌ {message}"
                )

            st.image(
                camera_image,
                caption="Captured Image",
                width=400
            )

    st.markdown("---")

    st.subheader("📅 Today's Attendance")

    attendance_df = get_attendance()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    today_df = attendance_df[
        attendance_df["Date"] == today
    ]

    if today_df.empty:

        st.info(
            "No attendance marked today."
        )

    else:

        st.dataframe(
            today_df,
            width="stretch",
            hide_index=True
        )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    "Smart Attendance System | "
    "Python + SQLite + Streamlit + OpenCV + Face Recognition"
)
