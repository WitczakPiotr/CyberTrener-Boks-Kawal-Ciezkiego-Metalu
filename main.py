import cv2
import numpy as np
import pyttsx4
import speech_recognition as sr
import threading


class CyberTrenerMenu:
    def __init__(self):
        try:
            self.engine = pyttsx4.init()
            self.engine.setProperty('rate', 160)
        except:
            self.engine = None

        self.recognizer = sr.Recognizer()
        self.state = "MENU"
        self.running = True
        self.width, self.height = 1280, 720

    def speak(self, text):
        if self.engine:
            self.engine.say(text)
            self.engine.runAndWait()

    def listen_commands(self):
        while self.running:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                try:
                    audio = self.recognizer.listen(source, timeout=5)
                    command = self.recognizer.recognize_google(audio, language="pl-PL").lower()
                    print(f"Komenda głosowa: {command}")

                    if "trening" in command or "zacznij" in command:
                        self.state = "TRENING"
                        self.speak("Zaczynamy sesję. Trzymaj gardę!")
                    elif "historia" in command or "wynik" in command:
                        self.state = "HISTORIA"
                        self.speak("Oto Twoja historia treningów.")
                    elif "menu" in command or "wróć" in command:
                        self.state = "MENU"
                        self.speak("Powrót do menu głównego.")
                    elif "wyjście" in command or "koniec" in command:
                        self.speak("Do zobaczenia mistrzu!")
                        self.running = False
                except:
                    pass

    def draw_hud(self, frame):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, self.height - 130), (self.width, self.height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        if self.state == "MENU":
            cv2.putText(frame, "CYBERTRENER BOKSU", (40, self.height - 80),
                        cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, "Powiedz: Trening, Historia lub Wyjscie", (40, self.height - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

        elif self.state == "HISTORIA":
            cv2.putText(frame, "HISTORIA (PLIKI CSV/JSON)", (40, self.height - 80),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 165, 0), 2)
            cv2.putText(frame, "Powiedz: Menu, aby wrocic", (40, self.height - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        elif self.state == "TRENING":
            cv2.putText(frame, "TRYB TRENINGU", (40, self.height - 80),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, "Powiedz: Menu, aby przerwac", (40, self.height - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    def run(self):
        # Powitanie i instrukcja komend
        intro_text = ("Witaj w Cybertrenerze Boksu. "
                      "Dostępne komendy to: zacznij trening, historia, menu oraz wyjście. "
                      "Słucham Twoich poleceń.")
        threading.Thread(target=lambda: self.speak(intro_text), daemon=True).start()

        threading.Thread(target=self.listen_commands, daemon=True).start()

        while self.running:
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            cv2.rectangle(frame, (0, 0), (self.width, self.height), (20, 20, 20), -1)

            self.draw_hud(frame)
            cv2.imshow("Cybertrener Boksu", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('t'):
                self.state = "TRENING"
            elif key == ord('h'):
                self.state = "HISTORIA"
            elif key == ord('m'):
                self.state = "MENU"
            elif key == ord('q'):
                self.running = False

        cv2.destroyAllWindows()


if __name__ == "__main__":
    app = CyberTrenerMenu()
    app.run()