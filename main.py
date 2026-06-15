import os
import sys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '2'

import warnings

warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf.symbol_database')

import customtkinter as ctk
import tkinter as tk
import cv2
from PIL import Image, ImageTk
import threading
import datetime
import json
import time
import random

from config import WIDTH, HEIGHT, HISTORY_FILE
from vision_engine import VisionManager
from voice_engine import VoiceManager
from ble_engine import BleManager


class CyberTrenerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("CyberTrener Boksu")
        self.geometry(f"{WIDTH}x{HEIGHT}")
        ctk.set_appearance_mode("dark")

        self.app_state = "MENU"
        self.running = True
        self.punch_count = 0
        self.training_start_time = None

        self.gotowy_na_cios = True

        self.menu_options = ["TRENING", "HISTORIA", "INSTRUKCJA", "WYJŚCIE"]
        self.menu_index = 0

        self.punch_options = ["10x PROSTE", "10x SIERPOWE", "10x PODBRÓDKOWE", "MIESZANY (30 ciosów)"]
        self.punch_index = 0

        self.plan_treningowy = []
        self.aktualny_etap = 0
        self.aktualny_wzorzec = {}

        self.vision = VisionManager()
        self.voice = VoiceManager()
        self.ble = BleManager(self.handle_ble_command)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        self.video_label = tk.Label(self.main_frame, bg="#111111", bd=0)
        self.hud_top = ctk.CTkLabel(self.main_frame, text="", font=ctk.CTkFont(size=26, weight="bold"),
                                    text_color="#F1C40F", fg_color="#1A1A1A", corner_radius=8, padx=15, pady=5)
        self.hud_bottom = ctk.CTkLabel(self.main_frame, text="", font=ctk.CTkFont(size=22, weight="bold"),
                                       text_color="#FFFFFF", fg_color="#1A1A1A", corner_radius=8, padx=15, pady=5)

        self.menu_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.menu_labels = []
        self.text_display = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(size=24), width=800, height=400,
                                           state="disabled")

        self.voice.speak("System gotowy.")
        self.set_state("MENU")
        self.update_camera()

        threading.Thread(target=self.command_loop, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self.zamknij_aplikacje)

    def set_state(self, new_state):
        if self.app_state == "TRENING" and new_state != "TRENING":
            self.ble.send_to_esp("STOP")

        self.app_state = new_state
        self.video_label.place_forget()
        self.hud_top.place_forget()
        self.hud_bottom.place_forget()
        self.menu_frame.place_forget()
        self.text_display.place_forget()

        if new_state == "MENU":
            self._buduj_centralne_menu(self.menu_options, self.menu_index, "CYBERTRENER")
        elif new_state == "WYBOR_CIOSU":
            self._buduj_centralne_menu(self.punch_options, self.punch_index, "WYBIERZ PLAN TRENINGOWY")
        elif new_state == "TRENING":
            self.video_label.place(relx=0.5, rely=0.5, anchor="center", width=WIDTH, height=HEIGHT)
            self.hud_top.place(relx=0.5, rely=0.05, anchor="n")
            self.hud_bottom.place(relx=0.5, rely=0.95, anchor="s")
        elif new_state == "HISTORIA":
            self.hud_top.configure(text="OSTATNIE TRENINGI (Wciśnij BACK aby wrócić)")
            self.hud_top.place(relx=0.5, rely=0.1, anchor="n")
            self.text_display.place(relx=0.5, rely=0.5, anchor="center")
            self.pokaz_historie()
        elif new_state == "INSTRUKCJA":
            self.hud_top.configure(text="USTAWIENIE KAMER (Wciśnij BACK aby wrócić)")
            self.hud_top.place(relx=0.5, rely=0.1, anchor="n")
            self.text_display.place(relx=0.5, rely=0.5, anchor="center")
            self.pokaz_instrukcje()

    def _buduj_centralne_menu(self, opcje, aktywny_index, tytul_tekst):
        for widget in self.menu_frame.winfo_children(): widget.destroy()
        self.menu_labels = []
        tytul = ctk.CTkLabel(self.menu_frame, text=tytul_tekst, font=ctk.CTkFont(size=50, weight="bold"),
                             text_color="#F1C40F")
        tytul.pack(pady=(0, 60))
        for opcja in opcje:
            lbl = ctk.CTkLabel(self.menu_frame, text=opcja, font=ctk.CTkFont(size=30))
            lbl.pack(pady=15)
            self.menu_labels.append(lbl)
        self._odswiez_podswietlenie_menu(opcje, aktywny_index)
        self.menu_frame.place(relx=0.5, rely=0.5, anchor="center")

    def _odswiez_podswietlenie_menu(self, opcje, aktywny_index):
        if not self.menu_labels: return
        for i, lbl in enumerate(self.menu_labels):
            if i == aktywny_index:
                lbl.configure(text=f"[ >   {opcje[i]}   < ]", text_color="#2ECC71",
                              font=ctk.CTkFont(size=40, weight="bold"))
            else:
                lbl.configure(text=opcje[i], text_color="#FFFFFF", font=ctk.CTkFont(size=30, weight="normal"))

    def update_camera(self):
        if not self.running: return

        if self.app_state == "TRENING":
            elapsed = "00:00"
            if self.training_start_time:
                dt = datetime.datetime.now() - self.training_start_time
                minutes, seconds = divmod(int(dt.total_seconds()), 60)
                elapsed = f"{minutes:02d}:{seconds:02d}"

            if self.plan_treningowy and self.aktualny_etap < len(self.plan_treningowy):
                aktualny_cios = self.plan_treningowy[self.aktualny_etap]["cios"]
                cel_powtorzen = self.plan_treningowy[self.aktualny_etap]["wymagane"]
            else:
                aktualny_cios = "ZAKOŃCZONO"
                cel_powtorzen = self.punch_count

            self.hud_bottom.configure(text=f"POWTÓRZENIA: {self.punch_count} / {cel_powtorzen}")

            if hasattr(self, 'aktualny_wzorzec') and self.aktualny_wzorzec and self.aktualny_etap < len(
                    self.plan_treningowy):
                event, bledy = self.vision.analyze_live(self.aktualny_wzorzec, self.gotowy_na_cios)

                if event == "TRACKING_LOST":
                    self.hud_top.configure(text="⚠️ SŁABA WIDOCZNOŚĆ! POPRAW KADR ⚠️", text_color="#FF4444")
                    if time.time() - getattr(self, 'ostatnie_ostrzezenie_mp', 0) > 4.0:
                        self.voice.speak("Słaba widoczność. Stań w kadrze.", interrupt=True)
                        self.ostatnie_ostrzezenie_mp = time.time()

                elif event == "PUNCH_REGISTERED" and self.gotowy_na_cios:
                    self.gotowy_na_cios = False

                    if bledy:
                        self.voice.speak(bledy[0], interrupt=True)
                        skrocony_blad = bledy[0].split('.')[0]
                        self.hud_top.configure(text=f"BŁĄD: {skrocony_blad.upper()}", text_color="#FF4444")
                    else:
                        self.punch_count += 1
                        etap = self.plan_treningowy[self.aktualny_etap]

                        if self.punch_count >= etap["wymagane"]:
                            self.hud_top.configure(text="SERIA ZAKOŃCZONA!", text_color="#2ECC71")
                            self.aktualny_etap += 1
                            self.vision.reset_state()
                            self.aktualny_wzorzec = {}
                            self.punch_count = 0

                            if self.aktualny_etap < len(self.plan_treningowy):
                                self.voice.speak("Świetnie! Zmiana ciosu.", interrupt=True)
                                self.after(2000, self._zaladuj_etap)
                            else:
                                self.voice.speak("Trening zakończony. Dobra robota.", interrupt=True)
                                self.ble.send_to_esp("STOP")
                                self.after(2000, lambda: self.set_state("MENU"))
                        else:
                            self.voice.speak("Cios poprawny. Wróć na pozycję.", interrupt=True)
                            self.hud_top.configure(text="CIOS ZALICZONY! WRÓĆ NA POZYCJĘ...", text_color="#2ECC71")
                            self.ble.send_to_esp(f"COUNT:{self.punch_count}")

                elif event == "READY":
                    if not self.gotowy_na_cios:
                        self.voice.speak("Gotowy.", interrupt=True)
                        self.gotowy_na_cios = True

                if self.vision.punch_state == "IDLE" and event != "TRACKING_LOST" and self.gotowy_na_cios:
                    self.hud_top.configure(text=f"TRENUJESZ: {aktualny_cios.replace('_', ' ')}   |   CZAS: {elapsed}",
                                           text_color="#F1C40F")

            frame = self.vision.get_frame()
            if frame is not None:
                cv2_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(cv2_image)
                imgtk = ImageTk.PhotoImage(image=pil_image)
                self.video_label.configure(image=imgtk)
                self.video_label.image = imgtk

        self.after(30, self.update_camera)

    def pokaz_historie(self):
        historia = self.get_history()
        self.text_display.configure(state="normal")
        self.text_display.delete("0.0", "end")
        self.text_display.insert("0.0", "\n\n".join(historia))
        self.text_display.configure(state="disabled")
        self.voice.speak("Oto twoja historia")

    def pokaz_instrukcje(self):
        self.text_display.configure(state="normal")
        self.text_display.delete("0.0", "end")
        self.text_display.insert("0.0",
                                 "\n1. Kamera patrzy na wprost.\n\n2. Telefon pod kątem 45 stopni.\n\nPad: Wciśnij BACK, aby wrócić.")
        self.text_display.configure(state="disabled")
        self.voice.speak("Instrukcja ustawienia")

    def handle_ble_command(self, cmd):
        self.after(0, lambda: self._process_ble_cmd(cmd))

    def _process_ble_cmd(self, cmd):
        if self.app_state == "MENU":
            if cmd == "NEXT":
                self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                self._odswiez_podswietlenie_menu(self.menu_options, self.menu_index)
            elif cmd == "SELECT":
                wybrano = self.menu_options[self.menu_index]
                if wybrano == "WYJŚCIE":
                    self.zamknij_aplikacje()
                else:
                    self.set_state(
                        {"TRENING": "WYBOR_CIOSU", "HISTORIA": "HISTORIA", "INSTRUKCJA": "INSTRUKCJA"}.get(wybrano,
                                                                                                           "MENU"))

        elif self.app_state == "WYBOR_CIOSU":
            if cmd == "NEXT":
                self.punch_index = (self.punch_index + 1) % len(self.punch_options)
                self._odswiez_podswietlenie_menu(self.punch_options, self.punch_index)
            elif cmd == "SELECT":
                self.rozpocznij_trening(self.punch_options[self.punch_index])

        if cmd == "BACK":
            self.set_state("MENU")

    def command_loop(self):
        while self.running:
            cmd = self.voice.listen()
            if not cmd: continue

            if any(x in cmd for x in ["menu", "wroc", "wróć"]):
                self.after(0, lambda: self.set_state("MENU"))
                self.voice.speak("Powrót", interrupt=True)
            elif self.app_state == "MENU" and "trening" in cmd:
                self.after(0, lambda: self.set_state("WYBOR_CIOSU"))
            elif self.app_state == "WYBOR_CIOSU":
                if "proste" in cmd:
                    self.after(0, lambda: self.rozpocznij_trening("10x PROSTE"))
                elif "sierpow" in cmd:
                    self.after(0, lambda: self.rozpocznij_trening("10x SIERPOWE"))
                elif "podbr" in cmd:
                    self.after(0, lambda: self.rozpocznij_trening("10x PODBRÓDKOWE"))
                elif "mieszan" in cmd:
                    self.after(0, lambda: self.rozpocznij_trening("MIESZANY (30 ciosów)"))

    def rozpocznij_trening(self, typ_planu):
        if "PROSTE" in typ_planu:
            self.plan_treningowy = [
                {"cios": "LEWY_PROSTY", "wymagane": 5, "json": "config_ciosy/wzorzec_lewy_prosty.json"},
                {"cios": "PRAWY_PROSTY", "wymagane": 5, "json": "config_ciosy/wzorzec_prawy_prosty.json"}
            ]
        elif "SIERPOWE" in typ_planu:
            self.plan_treningowy = [
                {"cios": "LEWY_SIERPOWY", "wymagane": 5, "json": "config_ciosy/wzorzec_lewy_sierpowy.json"},
                {"cios": "PRAWY_SIERPOWY", "wymagane": 5, "json": "config_ciosy/wzorzec_prawy_sierpowy.json"}
            ]
        elif "PODBRÓDKOWE" in typ_planu:
            self.plan_treningowy = [
                {"cios": "LEWY_PODBRODEK", "wymagane": 5, "json": "config_ciosy/wzorzec_lewy_podbrodek.json"},
                {"cios": "PRAWY_PODBRODEK", "wymagane": 5, "json": "config_ciosy/wzorzec_prawy_podbrodek.json"}
            ]
        else:
            self.plan_treningowy = [
                {"cios": "LEWY_PROSTY", "wymagane": 5, "json": "config_ciosy/wzorzec_lewy_prosty.json"},
                {"cios": "PRAWY_PROSTY", "wymagane": 5, "json": "config_ciosy/wzorzec_prawy_prosty.json"},
                {"cios": "LEWY_SIERPOWY", "wymagane": 5, "json": "config_ciosy/wzorzec_lewy_sierpowy.json"},
                {"cios": "PRAWY_SIERPOWY", "wymagane": 5, "json": "config_ciosy/wzorzec_prawy_sierpowy.json"},
                {"cios": "LEWY_PODBRODEK", "wymagane": 5, "json": "config_ciosy/wzorzec_lewy_podbrodek.json"},
                {"cios": "PRAWY_PODBRODEK", "wymagane": 5, "json": "config_ciosy/wzorzec_prawy_podbrodek.json"}
            ]

        self.aktualny_etap = 0
        self.set_state("TRENING")
        self.training_start_time = datetime.datetime.now()
        self.save_to_history(typ_planu)
        self.vision.reset_state()
        self._zaladuj_etap()

    def _zaladuj_etap(self):
        etap = self.plan_treningowy[self.aktualny_etap]
        self.punch_count = 0
        self.gotowy_na_cios = True

        if os.path.exists(etap["json"]):
            with open(etap["json"], "r", encoding="utf-8") as f:
                self.aktualny_wzorzec = json.load(f)
        else:
            print(f"BRAK PLIKU JSON: {etap['json']}!")
            return

        nazwa_mowiona = etap["cios"].replace('_', ' ')
        self.voice.speak(f"Przygotuj się. {etap['wymagane']} razy {nazwa_mowiona}.", interrupt=True)
        self.ble.send_to_esp(f"START:{etap['cios']}")

    def save_to_history(self, punch):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(HISTORY_FILE, "a", encoding="utf-8") as f: f.write(f"{now} - Trening: {punch}\n")

    def get_history(self):
        if not os.path.exists(HISTORY_FILE): return ["Brak zapisanych treningów."]
        with open(HISTORY_FILE, "r", encoding="utf-8") as f: return [line.strip() for line in f.readlines()[-10:]]

    def zamknij_aplikacje(self):
        self.running = False
        self.vision.release()
        self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = CyberTrenerGUI()
    app.mainloop()