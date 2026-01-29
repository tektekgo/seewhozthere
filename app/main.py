import cv2
import time
import os

# --- Configuration ---
# We will move this to a separate config file later.
# For now, you can change the RTSP URL when your camera arrives.
# The 'os.environ.get' is a good practice to avoid hardcoding secrets.
CAMERA_RTSP_URL = os.environ.get("C1_RTSP_URL", "rtsp://placeholder")
RECONNECT_DELAY_SECONDS = 10

def main():
    """
    Main function to connect to the camera and process the video stream.
    """
    print("--- SeeWhozThere Application Starting ---")
    print(f"Attempting to connect to camera at: {CAMERA_RTSP_URL}")

    while True:
        # The 'cv2.VideoCapture' object is how we connect to the camera.
        cap = cv2.VideoCapture(CAMERA_RTSP_URL)

        if not cap.isOpened():
            print(f"Error: Could not open camera stream.")
            print(f"Retrying in {RECONNECT_DELAY_SECONDS} seconds...")
            cap.release()
            time.sleep(RECONNECT_DELAY_SECONDS)
            continue

        print("Successfully connected to camera stream.")

        while True:
            # cap.read() returns a boolean (success) and the video frame.
            ret, frame = cap.read()

            # If 'ret' is False, it means we lost connection to the stream.
            if not ret:
                print("Error: Lost connection to the camera stream. Reconnecting...")
                break # Break the inner loop to trigger a reconnect.

            # --- AI PROCESSING WILL GO HERE ---
            # 1. TODO: Detect faces in the 'frame'.
            # 2. TODO: For each face, generate an embedding.
            # 3. TODO: Compare embedding to the database.
            # ------------------------------------

            # For now, we will just display the stream to show it's working.
            # We will remove this later when we run it as a background service.
            cv2.imshow("SeeWhozThere - Live Feed", frame)

            # Press 'q' to quit the application.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("'q' pressed. Shutting down.")
                cap.release()
                cv2.destroyAllWindows()
                return # Exit the main function and the script.

        # Clean up before the next reconnect attempt
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
