# CyberTrener-Boks-Kawal-Ciezkiego-Metalu 🥊

Projekt inteligentnego systemu wspomagania treningu bokserskiego, który łączy analizę obrazu (Computer Vision) z interfejsem głosowym. 

## 🎯 Cel Projektu
Stworzenie wirtualnego trenera, który dzięki ustawieniu dwóch kamer (pod kątem 45 stopni) będzie w stanie analizować technikę ciosów, korygować błędy w czasie rzeczywistym i prowadzić statystyki postępów użytkownika bez konieczności odrywania rąk od treningu.

## 🚀 Aktualny Stan Projektu (Maj 2026)

Projekt przeszedł z fazy pojedynczego skryptu na **architekturę modułową**, co zapewnia stabilność i pozwala na niezależny rozwój poszczególnych systemów.

### Kluczowe zmiany:
* **Refaktoryzacja kodu:** Rozbicie na pliki `main.py`, `vision_engine.py`, `voice_engine.py` i `config.py`.
* **Interfejs Głosowy:** Stabilne rozpoznawanie komend w języku polskim oraz system odpowiedzi lektora.
* **System Historii:** W pełni działający zapis sesji treningowych do pliku tekstowego `historia_treningow.txt`.
* **Tryb Wizji:** Implementacja podglądu z kamery w czasie rzeczywistym (Mirror Mode) aktywowanego komendą głosową.

## 📂 Struktura Plików
* `main.py` – Główny kontroler zarządzający stanami aplikacji.
* `vision_engine.py` – Moduł odpowiedzialny za przechwytywanie i przetwarzanie obrazu z kamer.
* `voice_engine.py` – Obsługa mikrofonu i syntezy mowy (Speech-to-Text & Text-to-Speech).
* `config.py` – Plik konfiguracyjny (wymiary okna, ścieżki do plików).

## 🥊 Funkcje Systemu
* **Komendy Głosowe:** "Trening", "Historia", "Instrukcja", "Menu", "Wróć".
* **Wybór Ciosów:** Obsługa ciosów prostych, sierpowych oraz podbródkowych.
* **Instrukcja Graficzna:** Wyświetlanie schematu poprawnego ustawienia stanowiska treningowego.
* **Podgląd Live:** Wyświetlanie obrazu z kamery podczas aktywnego treningu.

## 🛠️ Instalacja i Uruchomienie

1. Zainstaluj wymagane biblioteki:
   ```bash
   pip install opencv-python pyttsx4 SpeechRecognition PyAudio numpy
