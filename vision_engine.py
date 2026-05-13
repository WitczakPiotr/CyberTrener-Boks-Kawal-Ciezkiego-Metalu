import cv2
from config import WIDTH, HEIGHT


class VisionManager:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    def get_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None

        frame = cv2.flip(frame, 1)  # Lustrzane odbicie
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        return frame

    def release(self):
        self.cap.release()