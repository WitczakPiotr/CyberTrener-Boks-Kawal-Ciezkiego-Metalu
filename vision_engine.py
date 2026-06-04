import cv2
import numpy as np
import mediapipe as mp
from config import WIDTH, HEIGHT


class VisionManager:
    def __init__(self):
        # ==========================================
        # INICJALIZACJA KAMER
        # ==========================================
        # Kamera 1 (Główna - PC)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

        # Kamera 2 (Poboczna - np. Telefon przez Phone Link)
        self.cap2 = cv2.VideoCapture(1)

        # ==========================================
        # INICJALIZACJA MEDIAPIPE POSE
        # ==========================================
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_pose = mp.solutions.pose

        # --- Dwa osobne modele Pose ---
        # Tworzymy osobne instancje, aby perspektywy z dwóch kamer się nie gryzły
        self.pose1 = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.pose2 = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def get_frame(self):
        # Klatka bazowa - czarne tło pod obie kamery
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        # Obliczenia wymiarów na pół ekranu
        half_w = WIDTH // 2
        half_h = int(half_w * 9 / 16)
        y_offset = (HEIGHT - half_h) // 2 - 30

        # --- Obsługa Kamery 1 (Głównej) ---
        success1, frame1 = self.cap.read()
        if success1:
            frame1 = cv2.flip(frame1, 1)  # Lustrzane odbicie dla wygody treningu
            frame1 = cv2.resize(frame1, (half_w, half_h))

            # Nakładanie MediaPipe
            rgb_frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
            results1 = self.pose1.process(rgb_frame1)
            if results1.pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame1,
                    results1.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )
            frame[y_offset:y_offset + half_h, 0:half_w] = frame1
        else:
            cv2.putText(frame, "BRAK KAMERY 1", (half_w // 2 - 100, HEIGHT // 2), cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 0, 255), 2)

        # --- Obsługa Kamery 2 (Pobocznej) ---
        success2, frame2 = self.cap2.read()
        if success2:
            frame2 = cv2.flip(frame2, 1)
            frame2 = cv2.resize(frame2, (half_w, half_h))

            # Nakładanie MediaPipe
            rgb_frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
            results2 = self.pose2.process(rgb_frame2)
            if results2.pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame2,
                    results2.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )
            frame[y_offset:y_offset + half_h, half_w:WIDTH] = frame2
        else:
            cv2.putText(frame, "BRAK KAMERY Z TELEFONU", (half_w + half_w // 2 - 180, HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

        return frame

    def release(self):
        # Zwolnienie zasobów wizyjnych po zamknięciu programu
        self.cap.release()
        if self.cap2.isOpened():
            self.cap2.release()
        self.pose1.close()
        self.pose2.close()