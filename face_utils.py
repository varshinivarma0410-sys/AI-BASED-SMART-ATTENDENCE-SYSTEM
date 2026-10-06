import cv2
import os
import sqlite3
from datetime import datetime
import numpy as np

DATABASE = "data/attendance.db"
FACE_FOLDER = "faces"


def mark_attendance(student_id):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    cursor.execute(
        """
        SELECT id FROM attendance
        WHERE student_id = ? AND date = ?
        """,
        (student_id, today)
    )

    already_marked = cursor.fetchone()

    if already_marked:
        print("Attendance already marked for today.")
    else:
        cursor.execute(
            """
            INSERT INTO attendance
            (student_id, date, time, status)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, today, current_time, "Present")
        )

        connection.commit()
        print("Attendance marked successfully!")

    connection.close()


def recognize_face():

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    images = []
    labels = []
    names = {}

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id, name, roll_number FROM students"
    )

    students = cursor.fetchall()
    connection.close()

    if not students:
        print("No students registered.")
        return

    for student_id, name, roll_number in students:

        image_path = os.path.join(
            FACE_FOLDER,
            f"{roll_number}.jpg"
        )

        if os.path.exists(image_path):

            image = cv2.imread(
                image_path,
                cv2.IMREAD_GRAYSCALE
            )

            images.append(image)
            labels.append(student_id)

            names[student_id] = (
                name,
                roll_number
            )

    if not images:
        print("No face images found.")
        return

    recognizer.train(
        images,
        np.array(labels)
    )

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Smart Attendance System Started.")
    print("Look at the camera.")
    print("Press Q to quit.")

    attendance_marked = set()

    while True:

        ret, frame = camera.read()

        if not ret:
            print("Error: Could not read webcam.")
            break

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        for (x, y, w, h) in faces:

            face = gray[y:y+h, x:x+w]

            student_id, confidence = recognizer.predict(face)

            if confidence < 80 and student_id in names:

                name, roll_number = names[student_id]

                label = f"{name} - {roll_number}"

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x+w, y+h),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    label,
                    (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                if student_id not in attendance_marked:

                    mark_attendance(student_id)

                    attendance_marked.add(student_id)

            else:

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x+w, y+h),
                    (0, 0, 255),
                    2
                )

                cv2.putText(
                    frame,
                    "Unknown",
                    (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

        cv2.imshow(
            "AI Smart Attendance System",
            frame
        )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    recognize_face()