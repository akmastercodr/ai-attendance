import cv2
import os
import time
from register_faces import register_faces

def capture_and_register():
    """
    Opens the webcam to capture a face image and then registers it.
    """
    name = input("Enter the name of the person to register: ").strip()
    if not name:
        print("Name cannot be empty.")
        return
    
    dept = input("Enter Department: ").strip()
    role = input("Enter Role: ").strip()
    
    metadata = {
        "department": dept,
        "role": role,
        "registration_date": str(time.time())
    }

    save_dir = "data/known_faces"
    os.makedirs(save_dir, exist_ok=True)
    img_path = os.path.join(save_dir, f"{name}.jpg")

    cap = cv2.VideoCapture(0)
    print(f"Position your face in the camera for {name}.")
    print("Press 's' to capture and save, or 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        cv2.imshow("Capture Face", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            cv2.imwrite(img_path, frame)
            print(f"Captured and saved to {img_path}")
            break
        elif key == ord('q'):
            print("Capture cancelled.")
            cap.release()
            cv2.destroyAllWindows()
            return

    cap.release()
    cv2.destroyAllWindows()

    # Automatically register the new face
    print("Updating vector database with metadata...")
    register_faces(save_dir, default_metadata=metadata)
    print(f"Successfully registered {name}!")

if __name__ == "__main__":
    capture_and_register()
