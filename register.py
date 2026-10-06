import cv2
import os
import sqlite3

DATABASE = "data/attendance.db"
FACE_FOLDER = "faces"


def register_student():
    name = input("Enter student name: ")
    roll_number = input("Enter roll number: ")

    # Create faces folder if it doesn't exist
    os.makedirs(FACE_FOLDER, exist_ok=True)

    # Open webcam
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Camera opened.")
    print("Look at the camera.")
    print("Press SPACE to capture the face.")
    print("Press Q to cancel.")

    while True:
        ret, frame = camera.read()

        if not ret:
            print("Error: Could not read from webcam.")
            break

        cv2.imshow("Student Registration", frame)

        key = cv2.waitKey(1) & 0xFF

        # Capture image
        if key == ord(" "):
            image_path = os.path.join(
                FACE_FOLDER,
                f"{roll_number}.jpg"
            )

            cv2.imwrite(image_path, frame)

            # Save student details to database
            connection = sqlite3.connect(DATABASE)
            cursor = connection.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO students (name, roll_number)
                    VALUES (?, ?)
                    """,
                    (name, roll_number)
                )

                connection.commit()
                print("\nStudent registered successfully!")
                print(f"Name: {name}")
                print(f"Roll Number: {roll_number}")
                print(f"Face saved: {image_path}")

            except sqlite3.IntegrityError:
                print("\nError: This roll number already exists.")

            finally:
                connection.close()

            break

        # Cancel
        elif key == ord("q"):
            print("Registration cancelled.")
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    register_student()