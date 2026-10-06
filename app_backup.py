import streamlit as st
import sqlite3
import pandas as pd

DATABASE = "data/attendance.db"

st.set_page_config(
    page_title="AI Smart Attendance System",
    page_icon="📋",
    layout="wide"
)

st.title("📋 AI-Based Smart Attendance System")
st.write("Attendance Dashboard")

connection = sqlite3.connect(DATABASE)

query = """
SELECT
    students.name AS Name,
    students.roll_number AS Roll_Number,
    attendance.date AS Date,
    attendance.time AS Time,
    attendance.status AS Status
FROM attendance
JOIN students
ON attendance.student_id = students.id
ORDER BY attendance.date DESC, attendance.time DESC
"""

data = pd.read_sql_query(query, connection)

connection.close()

st.subheader("📊 Attendance Records")

if data.empty:
    st.info("No attendance records found.")
else:
    st.dataframe(
        data,
        use_container_width=True
    )

    st.subheader("📈 Attendance Summary")

    total_records = len(data)
    present_count = len(
        data[data["Status"] == "Present"]
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Total Attendance Records",
            total_records
        )

    with col2:
        st.metric(
            "Present",
            present_count
        )

    st.subheader("📥 Download Attendance")

    csv = data.to_csv(index=False)

    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="attendance_report.csv",
        mime="text/csv"
    )