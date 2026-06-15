import pyttsx4
import speech_recognition as sr
import threading
import queue


class VoiceManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()

        self.q = queue.Queue()
        self.worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.worker_thread.start()

    def _tts_worker(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass

        try:
            engine = pyttsx4.init()
            engine.setProperty('rate', 175)
            voices = engine.getProperty('voices')
            for voice in voices:
                if "pol" in voice.name.lower() or "pl" in voice.id.lower():
                    engine.setProperty('voice', voice.id)
                    break
        except Exception as e:
            print(f"Nie udało się odpalić TTS: {e}")
            engine = None

        while True:
            text = self.q.get()
            if text is None:
                break

            if engine:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except:
                    pass
            self.q.task_done()

    def speak(self, text, interrupt=False):
        if interrupt:
            with self.q.mutex:
                self.q.queue.clear()

        self.q.put(text)

    def listen(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
                return self.recognizer.recognize_google(audio, language="pl-PL").lower()
            except:
                return ""