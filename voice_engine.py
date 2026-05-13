import pyttsx4
import speech_recognition as sr
import threading

class VoiceManager:
    def __init__(self):
        try:
            self.engine = pyttsx4.init()
            self.engine.setProperty('rate', 175)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if "pol" in voice.name.lower() or "pl" in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
        except:
            self.engine = None
        self.recognizer = sr.Recognizer()

    def speak(self, text):
        if self.engine:
            def _speak():
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except:
                    pass
            threading.Thread(target=_speak, daemon=True).start()

    def listen(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
                return self.recognizer.recognize_google(audio, language="pl-PL").lower()
            except:
                return ""