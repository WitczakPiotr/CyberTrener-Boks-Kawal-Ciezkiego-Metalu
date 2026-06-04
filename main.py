import cv2
import numpy as np
import threading
import datetime
import os
import sys

from config import WIDTH, HEIGHT, HISTORY_FILE
from voice_engine import VoiceManager
from vision_engine import VisionManager
from ble_engine import BleManager  # Nowy moduł pod ESP32


class CyberTrenerApp:
    def __init__(self):
        # ==========================================
        # INICJALIZACJA SYSTEMÓW BAZOWYCH
        # ==========================================
        self.voice = VoiceManager()
        self.vision = VisionManager()
        self.state = "MENU"
        self.punch_type = None
        self.running = True

        # ==========================================
        # ZMIENNE POD LOGIKĘ SPRZĘTOWĄ I STATYSTYKI
        # ==========================================
        self.punch_count = 0
        self.training_start_time = None

        # Zmienne nawigacyjne potrzebne do sterowania z pada (NEXT/SELECT)
        self.menu_options = ["TRENING", "HISTORIA", "INSTRUKCJA", "WYJSCIE"]
        self.menu_index = 0
        self.punch_options = ["PROSTY", "SIERPOWY", "PODBRODKOWY"]
        self.punch_index = 0

        # --- Podpięcie asynchronicznego menedżera BLE ---
        self.ble = BleManager(self.handle_ble_command)

    def handle_ble_command(self, cmd):
        """Obsługa sprzętowych komend przychodzących z ESP32"""
        if cmd == "NEXT":
            if self.state == "MENU":
                self.menu_index = (self.menu_index + 1) % len(self.menu_options)
            elif self.state == "WYBOR_CIOSU":
                self.punch_index = (self.punch_index + 1) % len(self.punch_options)
            elif self.state == "TRENING":
                # Symulacja zliczania ciosu po kliknięciu przycisku na padzie
                self.punch_count += 1
                self.ble.send_to_esp(f"COUNT:{self.punch_count}")

        elif cmd == "SELECT":
            if self.state == "MENU":
                selected = self.menu_options[self.menu_index]
                if selected == "TRENING":
                    self.state = "WYBOR_CIOSU"
                    self.voice.speak("Wybierz rodzaj ciosu")
                elif selected == "HISTORIA":
                    self.state = "HISTORIA"
                    self.voice.speak("Oto twoja historia")
                elif selected == "INSTRUKCJA":
                    self.state = "INSTRUKCJA"
                    self.voice.speak("Instrukcja ustawienia")
                elif selected == "WYJSCIE":
                    self.voice.speak("Zamykam program")
                    self.running = False
            elif self.state == "WYBOR_CIOSU":
                punch = self.punch_options[self.punch_index]
                self.punch_type = punch
                self.state = "TRENING"

                # --- Przygotowanie statystyk przed treningiem ---
                self.punch_count = 0
                self.training_start_time = datetime.datetime.now()
                self.save_to_history(punch)

                self.ble.send_to_esp(f"START:{punch}")
                self.voice.speak(f"Start treningu {punch}")

        elif cmd == "BACK":
            if self.state == "TRENING":
                self.ble.send_to_esp("STOP")
            self.state = "MENU"
            self.punch_type = None
            self.voice.speak("Powrot")

    def save_to_history(self, punch):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{now} - Trening: {punch}\n")

    def get_history(self):
        if not os.path.exists(HISTORY_FILE):
            return ["Brak zapisanych treningow"]
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            # Zwracamy tylko ostatnie 8 linijek zeby zmieściły się na ekranie
            return [line.strip() for line in f.readlines()[-8:]]

    def command_loop(self):
        """Obsługa standardowych komend głosowych w osobnym wątku"""
        while self.running:
            cmd = self.voice.listen()
            if not cmd: continue
            print(f"Komenda: {cmd}")

            # --- POWRÓT ---
            if any(x in cmd for x in ["menu", "wroc", "wróć", "powrot", "powrót"]):
                if self.state == "TRENING":
                    self.ble.send_to_esp("STOP")
                self.state = "MENU"
                self.punch_type = None
                self.voice.speak("Powrot")

            # --- NAWIGACJA MENU ---
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

            # --- WYBÓR CIOSU ---
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

                    # Przygotowanie zmiennych pod wyświetlanie statystyk Live
                    self.punch_count = 0
                    self.training_start_time = datetime.datetime.now()

                    self.save_to_history(punch)
                    self.ble.send_to_esp(f"START:{punch}")
                    self.voice.speak(f"Start treningu {punch}")

    def draw_hud(self, frame):
        # ==========================================
        # RYSOWANIE INTERFEJSU GRAFICZNEGO (HUD)
        # ==========================================
        # Pasek dolny - lekko przezroczysty
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, HEIGHT - 120), (WIDTH, HEIGHT), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        if self.state == "MENU":
            cv2.putText(frame, "CYBERTRENER - MENU (Obsluga BLE)", (40, HEIGHT - 70), cv2.FONT_HERSHEY_DUPLEX, 1.2,
                        (255, 255, 255), 2)
            # Wyświetlanie aktywnego elementu dla sterowania sprzętowego
            menu_text = f"Pad/Glos: [ Wybrano: > {self.menu_options[self.menu_index]} < ]"
            cv2.putText(frame, menu_text, (40, HEIGHT - 30), 1, 1.5, (0, 255, 255), 2)

        elif self.state == "WYBOR_CIOSU":
            cv2.putText(frame, f"WYBIERZ CIOS: [ > {self.punch_options[self.punch_index]} < ]", (40, HEIGHT - 60),
                        cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 255), 2)

        elif self.state == "TRENING":
            # Obliczanie upłyniętego czasu od rozpoczęcia treningu
            elapsed = "00:00"
            if self.training_start_time:
                dt = datetime.datetime.now() - self.training_start_time
                minutes, seconds = divmod(int(dt.total_seconds()), 60)
                elapsed = f"{minutes:02d}:{seconds:02d}"

            cv2.putText(frame, f"TRENUJESZ: {self.punch_type}  |  CZAS: {elapsed}", (40, HEIGHT - 70),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 255, 0), 2)
            cv2.putText(frame, f"POWTORZENIA: {self.punch_count}  (Oczekuje na pad ESP32)", (40, HEIGHT - 30), 1, 1.3,
                        (255, 255, 255), 2)

        elif self.state == "HISTORIA":
            cv2.putText(frame, "OSTATNIE TRENINGI (Wcisnij BACK na padzie aby wrocic):", (50, 80),
                        cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 255), 2)
            for i, line in enumerate(self.get_history()):
                cv2.putText(frame, line, (50, 140 + i * 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 1)

        elif self.state == "INSTRUKCJA":
            cv2.putText(frame, "USTAWIENIE KAMER (45 STOPNI) - Wcisnij BACK aby wrocic", (200, 80),
                        cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 255), 2)
            cx, cy = 640, 320
            cv2.circle(frame, (cx, cy + 120), 30, (0, 255, 0), -1)
            cv2.line(frame, (cx, cy + 120), (cx - 200, cy - 30), (255, 255, 255), 2)
            cv2.line(frame, (cx, cy + 120), (cx + 200, cy - 30), (255, 255, 255), 2)

    def run(self):
        cv2.namedWindow("Cybertrener Boksu")
        # Odpalamy nasłuchiwanie jako demon
        threading.Thread(target=self.command_loop, daemon=True).start()
        self.voice.speak("System gotowy.")

        while self.running:
            if self.state == "TRENING":
                frame = self.vision.get_frame()
                # Zabezpieczenie przed brakiem obrazu z kamer
                if frame is None:
                    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            else:
                # Czyste tło dla menu
                frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
                cv2.rectangle(frame, (0, 0), (WIDTH, HEIGHT), (15, 15, 15), -1)

            self.draw_hud(frame)
            cv2.imshow("Cybertrener Boksu", frame)

            # Zamknięcie klawiszem 'Q' lub "iksem"
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
            if cv2.getWindowProperty("Cybertrener Boksu", cv2.WND_PROP_VISIBLE) < 1:
                self.running = False
                break

        self.vision.release()
        cv2.destroyAllWindows()

        # Twarde wyjście wymagane by poprawnie ubić asynchroniczną pętlę Bluetooth w tle
        sys.exit(0)


if __name__ == "__main__":
    app = CyberTrenerApp()
    app.run()