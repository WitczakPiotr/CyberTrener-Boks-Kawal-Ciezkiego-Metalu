import cv2
import numpy as np
import threading
import datetime
import os

from config import WIDTH, HEIGHT, HISTORY_FILE
from voice_engine import VoiceManager
from vision_engine import VisionManager


class CyberTrenerApp:
    def __init__(self):
        self.voice = VoiceManager()
        self.vision = VisionManager()
        self.state = "MENU"
        self.punch_type = None
        self.running = True

    def save_to_history(self, punch):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{now} - Trening: {punch}\n")

    def get_history(self):
        if not os.path.exists(HISTORY_FILE):
            return ["Brak zapisanych treningow"]
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines()[-8:]]

    def command_loop(self):
        while self.running:
            cmd = self.voice.listen()
            if not cmd: continue
            print(f"Komenda: {cmd}")

            if any(x in cmd for x in ["menu", "wroc", "wróć", "powrot", "powrót"]):
                self.state = "MENU"
                self.punch_type = None
                self.voice.speak("Powrot")

            elif self.state == "MENU":
                if "trening" in cmd:
                    self.state = "WYBOR_CIOSU"
                    self.voice.speak("Wybierz rodzaj ciosu")
                elif "historia" in cmd:
                    self.state = "HISTORIA"
                    self.voice.speak("Oto twoja historia")
                elif "instrukcja" in cmd:
                    self.state = "INSTRUKCJA"
                    self.voice.speak("Instrukcja ustawienia")
                elif any(x in cmd for x in ["wyjscie", "wyjście", "koniec"]):
                    self.voice.speak("Zamykam program")
                    self.running = False

            elif self.state == "WYBOR_CIOSU":
                punch = None
                if "prosty" in cmd:
                    punch = "PROSTY"
                elif "sierpowy" in cmd:
                    punch = "SIERPOWY"
                elif any(x in cmd for x in ["podbrodkowy", "podbródkowy", "podbrodek", "podbródek"]):
                    punch = "PODBRODKOWY"

                if punch:
                    self.punch_type = punch
                    self.state = "TRENING"
                    self.save_to_history(punch)
                    self.voice.speak(f"Start treningu {punch}")

    def draw_hud(self, frame):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, HEIGHT - 120), (WIDTH, HEIGHT), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        if self.state == "MENU":
            cv2.putText(frame, "MENU GLOWNE", (40, HEIGHT - 70), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2)
            cv2.putText(frame, "Trening | Historia | Instrukcja | Wyjscie", (40, HEIGHT - 30), 1, 1, (0, 255, 0), 1)
        elif self.state == "WYBOR_CIOSU":
            cv2.putText(frame, "WYBIERZ: PROSTY | SIERPOWY | PODBRODKOWY", (40, HEIGHT - 60), cv2.FONT_HERSHEY_DUPLEX,
                        1, (0, 255, 255), 2)
        elif self.state == "TRENING":
            cv2.putText(frame, f"TRENUJESZ: {self.punch_type}", (40, HEIGHT - 70), cv2.FONT_HERSHEY_DUPLEX, 1.2,
                        (0, 255, 0), 2)
            cv2.putText(frame, "Powiedz MENU aby przerwac", (40, HEIGHT - 30), 1, 1, (255, 255, 255), 1)
        elif self.state == "HISTORIA":
            cv2.putText(frame, "OSTATNIE TRENINGI:", (50, 80), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 255), 2)
            for i, line in enumerate(self.get_history()):
                cv2.putText(frame, line, (50, 140 + i * 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 1)
        elif self.state == "INSTRUKCJA":
            cv2.putText(frame, "USTAWIENIE KAMER (45 STOPNI)", (400, 80), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 255), 2)
            cx, cy = 640, 320
            cv2.circle(frame, (cx, cy + 120), 30, (0, 255, 0), -1)
            cv2.line(frame, (cx, cy + 120), (cx - 200, cy - 30), (255, 255, 255), 2)
            cv2.line(frame, (cx, cy + 120), (cx + 200, cy - 30), (255, 255, 255), 2)

    def run(self):
        cv2.namedWindow("Cybertrener Boksu")
        threading.Thread(target=self.command_loop, daemon=True).start()
        self.voice.speak("System gotowy.")

        while self.running:
            if self.state == "TRENING":
                frame = self.vision.get_frame()
                if frame is None:
                    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            else:
                frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
                cv2.rectangle(frame, (0, 0), (WIDTH, HEIGHT), (15, 15, 15), -1)

            self.draw_hud(frame)
            cv2.imshow("Cybertrener Boksu", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.vision.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    app = CyberTrenerApp()
    app.run()