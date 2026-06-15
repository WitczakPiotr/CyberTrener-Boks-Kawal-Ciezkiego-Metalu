import cv2
import numpy as np
import mediapipe as mp
import threading
import time
from config import WIDTH, HEIGHT


def calculate_true_angle(a_norm, b_norm, c_norm, width, height):
    a = np.array([a_norm.x * width, a_norm.y * height])
    b = np.array([b_norm.x * width, b_norm.y * height])
    c = np.array([c_norm.x * width, c_norm.y * height])
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return float(360 - angle if angle > 180.0 else angle)


class CameraWorker:
    def __init__(self, camera_id, target_w, target_h, rotation=None):
        self.camera_id = camera_id
        self.width = target_w
        self.height = target_h
        self.running = True
        self.rotation = rotation

        self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5,
                                           model_complexity=0)

        self.latest_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.latest_landmarks = None

        if not self.cap.isOpened():
            cv2.putText(self.latest_frame, f"BRAK KAMERY (ID: {self.camera_id})", (10, self.height // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()

    def _process_loop(self):
        while self.running:
            if not self.cap.isOpened():
                time.sleep(0.1)
                continue

            success, frame = self.cap.read()
            if success:
                if self.rotation is not None:
                    frame = cv2.rotate(frame, self.rotation)

                frame = cv2.flip(frame, 1)

                h, w, _ = frame.shape
                target_aspect = self.width / self.height
                frame_aspect = w / h

                if frame_aspect > target_aspect:
                    new_w = int(h * target_aspect)
                    offset = (w - new_w) // 2
                    frame = frame[:, offset:offset + new_w]
                else:
                    new_h = int(w / target_aspect)
                    offset = (h - new_h) // 2
                    frame = frame[offset:offset + new_h, :]

                frame = cv2.resize(frame, (self.width, self.height))
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(rgb_frame)

                if results.pose_landmarks:
                    self.latest_landmarks = results.pose_landmarks
                    for i in range(11):
                        results.pose_landmarks.landmark[i].visibility = 0.0

                    self.mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS,
                                                   landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style())
                self.latest_frame = frame
            else:
                time.sleep(0.01)

    def stop(self):
        self.running = False
        self.thread.join(timeout=1.0)
        self.cap.release()
        self.pose.close()


class VisionManager:
    def __init__(self):
        self.phone_w = 405
        self.phone_h = HEIGHT
        self.laptop_w = WIDTH - self.phone_w
        self.laptop_h = int(self.laptop_w * 9 / 16)
        self.laptop_y_offset = (HEIGHT - self.laptop_h) // 2

        self.punch_state = "IDLE"
        self.peak_val = 0

        # --- Zmienne do Filtru Poziomego (Sierpowe) ---
        self.start_val_x = 0
        self.max_droga_x = 0

        self.peak_angle = 0
        self.peak_garda = 0
        self.return_start_time = 0

        self.worker1 = CameraWorker(0, self.laptop_w, self.laptop_h, rotation=None)
        self.worker2 = CameraWorker(1, self.phone_w, self.phone_h, rotation=None)

    def get_frame(self):
        canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        canvas[self.laptop_y_offset:self.laptop_y_offset + self.laptop_h, 0:self.laptop_w] = self.worker1.latest_frame
        canvas[0:HEIGHT, self.laptop_w:WIDTH] = self.worker2.latest_frame
        return canvas

    def reset_state(self):
        self.punch_state = "IDLE"
        self.peak_val = 0
        self.start_val_x = 0
        self.max_droga_x = 0
        self.peak_angle = 0
        self.peak_garda = 0
        self.return_start_time = 0

    def _sprawdz_widocznosc_reki(self, landmarks, indeksy_reki):
        widocznosci = [landmarks.landmark[i].visibility for i in indeksy_reki]
        return sum(widocznosci) / len(widocznosci)

    def analyze_live(self, wzorzec, gotowy_na_cios=True):
        lm_bok = self.worker1.latest_landmarks
        lm_przod = self.worker2.latest_landmarks

        if not wzorzec or not lm_bok or not lm_przod:
            return None, []

        typ_ciosu = wzorzec.get("nazwa_ciosu", "")
        if not typ_ciosu:
            return None, []

        lm_b = lm_bok.landmark
        lm_p = lm_przod.landmark
        w_side, h_side = self.worker1.width, self.worker1.height

        if "LEWY" in typ_ciosu:
            indeksy_uderzajacej = [12, 14, 16]
            uderzajacy_nadgarstek_y = lm_p[16].y
            uderzajacy_nadgarstek_x = lm_p[16].x  # Śledzimy na osi X
            uderzajacy_bark_y = lm_p[12].y
            uderzajacy_lokiec_y = lm_p[14].y

            garda_nadgarstek_y = lm_p[15].y
            garda_bark_y = lm_p[11].y

            kat_lokcia = calculate_true_angle(lm_b[12], lm_b[14], lm_b[16], w_side, h_side)
        else:
            indeksy_uderzajacej = [11, 13, 15]
            uderzajacy_nadgarstek_y = lm_p[15].y
            uderzajacy_nadgarstek_x = lm_p[15].x  # Śledzimy na osi X
            uderzajacy_bark_y = lm_p[11].y
            uderzajacy_lokiec_y = lm_p[13].y

            garda_nadgarstek_y = lm_p[16].y
            garda_bark_y = lm_p[12].y

            kat_lokcia = calculate_true_angle(lm_b[11], lm_b[13], lm_b[15], w_side, h_side)

        wid_przod_uderzajaca = self._sprawdz_widocznosc_reki(lm_przod, indeksy_uderzajacej)
        if wid_przod_uderzajaca < 0.40:
            self.reset_state()
            return "TRACKING_LOST", []

        garda_diff = garda_nadgarstek_y - garda_bark_y
        reka_w_gorze = uderzajacy_nadgarstek_y < uderzajacy_bark_y + 0.35

        # Bezpieczniki przed zawieszeniem
        if self.punch_state == "IDLE" and not gotowy_na_cios:
            return "READY", []

        if self.punch_state == "RETURNING" and (time.time() - self.return_start_time > 1.5):
            self.punch_state = "IDLE"
            return "READY", []

        # ==========================================
        # MASZYNA STANÓW
        # ==========================================
        if "PROSTY" in typ_ciosu:
            if self.punch_state == "IDLE":
                if gotowy_na_cios and reka_w_gorze and (100 < kat_lokcia < 150):
                    self.punch_state = "EXTENDING"
                    self.peak_val = kat_lokcia
                    self.peak_garda = garda_diff
            elif self.punch_state == "EXTENDING":
                if kat_lokcia > self.peak_val:
                    self.peak_val = kat_lokcia
                    self.peak_garda = garda_diff

                if kat_lokcia < self.peak_val - 15:
                    if self.peak_val > 140:
                        self.punch_state = "RETURNING"
                        self.return_start_time = time.time()
                        errors = self._ocen_cios("PROSTY", wzorzec, self.peak_val, self.peak_garda)
                        return "PUNCH_REGISTERED", errors
                    else:
                        self.punch_state = "IDLE"
            elif self.punch_state == "RETURNING":
                if kat_lokcia < 130 or uderzajacy_nadgarstek_y > uderzajacy_bark_y + 0.1:
                    self.punch_state = "IDLE"
                    return "READY", []

        elif "SIERPOWY" in typ_ciosu:
            if self.punch_state == "IDLE":
                if gotowy_na_cios and reka_w_gorze and uderzajacy_lokiec_y < uderzajacy_bark_y + 0.15:
                    self.punch_state = "EXTENDING"
                    self.peak_val = uderzajacy_lokiec_y
                    # Zapisujemy początkową pozycję nadgarstka w poziomie
                    self.start_val_x = uderzajacy_nadgarstek_x
                    self.max_droga_x = 0
                    self.peak_angle = kat_lokcia
                    self.peak_garda = garda_diff
            elif self.punch_state == "EXTENDING":
                if uderzajacy_lokiec_y < self.peak_val:
                    self.peak_val = uderzajacy_lokiec_y
                    self.peak_angle = kat_lokcia
                    self.peak_garda = garda_diff

                # Śledzimy, jaki max dystans przebyła pięść w poziomie
                aktualna_droga_x = abs(uderzajacy_nadgarstek_x - self.start_val_x)
                if aktualna_droga_x > self.max_droga_x:
                    self.max_droga_x = aktualna_droga_x

                if uderzajacy_lokiec_y > self.peak_val + 0.05:
                    # FILTR POZIOMY (OŚ X): Ręka musiała zamachnąć się w poziomie o min. 8% kadru
                    if self.max_droga_x > 0.08:
                        self.punch_state = "RETURNING"
                        self.return_start_time = time.time()
                        errors = self._ocen_cios("SIERPOWY", wzorzec, self.peak_angle, self.peak_garda)
                        return "PUNCH_REGISTERED", errors
                    else:
                        # Ręka nie poszła w bok - to był tylko skręt ciała albo balans
                        self.punch_state = "IDLE"
            elif self.punch_state == "RETURNING":
                if uderzajacy_lokiec_y > uderzajacy_bark_y + 0.1:
                    self.punch_state = "IDLE"
                    return "READY", []

        elif "PODBRODEK" in typ_ciosu:
            if self.punch_state == "IDLE":
                if gotowy_na_cios and uderzajacy_nadgarstek_y < uderzajacy_bark_y + 0.1:
                    self.punch_state = "EXTENDING"
                    self.peak_val = uderzajacy_nadgarstek_y
                    self.peak_angle = kat_lokcia
                    self.peak_garda = garda_diff
            elif self.punch_state == "EXTENDING":
                if uderzajacy_nadgarstek_y < self.peak_val:
                    self.peak_val = uderzajacy_nadgarstek_y
                    self.peak_angle = kat_lokcia
                    self.peak_garda = garda_diff

                if uderzajacy_nadgarstek_y > self.peak_val + 0.05:
                    self.punch_state = "RETURNING"
                    self.return_start_time = time.time()
                    errors = self._ocen_cios("PODBRODEK", wzorzec, self.peak_angle, self.peak_garda)
                    return "PUNCH_REGISTERED", errors
            elif self.punch_state == "RETURNING":
                if uderzajacy_nadgarstek_y > uderzajacy_bark_y + 0.1:
                    self.punch_state = "IDLE"
                    return "READY", []

        return None, []

    def _ocen_cios(self, kategoria, wzorzec, osiagniety_kat, osiagnieta_garda_diff):
        errors = []

        if osiagnieta_garda_diff > 0.15:
            errors.append("Opuszczona garda. Podnieś drugą rękę do brody, żeby chronić głowę.")

        lm_bok = self.worker1.latest_landmarks
        typ_ciosu = wzorzec["nazwa_ciosu"]

        if "LEWY" in typ_ciosu:
            wid_bok_uderzajaca = self._sprawdz_widocznosc_reki(lm_bok, [12, 14, 16])
        else:
            wid_bok_uderzajaca = self._sprawdz_widocznosc_reki(lm_bok, [11, 13, 15])

        if wid_bok_uderzajaca > 0.50:
            docelowy_kat = wzorzec.get("max_kat_lokcia", 140)

            if kategoria == "PROSTY":
                if osiagniety_kat < docelowy_kat - 25:
                    errors.append("Ramię było za słabo wyprostowane. Wypchnij pięść mocniej do przodu.")

            elif kategoria == "SIERPOWY":
                if osiagniety_kat < docelowy_kat - 30:
                    errors.append("Za mocno zgięty łokieć. Rozłóż szerzej ramię.")
                elif osiagniety_kat > docelowy_kat + 30:
                    errors.append("Ręka ucieka na boki. Zagnij mocniej łokieć.")

            elif kategoria == "PODBRODEK":
                if osiagniety_kat < docelowy_kat - 30:
                    errors.append("Ręka za blisko ciała. Otwórz trochę łokieć.")
                elif osiagniety_kat > docelowy_kat + 30:
                    errors.append("Zbyt prosta ręka. Ugnij łokieć mocniej.")

        return errors

    def release(self):
        self.worker1.stop()
        self.worker2.stop()