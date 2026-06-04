#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <TFT_eSPI.h> // Biblioteka do obsługi ekranu LilyGO

// Piny przycisków
#define BTN_NEXT 47   
#define BTN_SELECT 0  

// UUID dla serwisu BLE UART
#define SERVICE_UUID           "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_RX "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_TX "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

TFT_eSPI tft = TFT_eSPI();
BLECharacteristic *pTxCharacteristic;
bool deviceConnected = false;

unsigned long btnSelectPressTime = 0;
bool isSelectPressed = false;

// Zmienne treningu
bool wTreningu = false;
unsigned long startTreninguMilis = 0;
int powtorzenia = 0;

// Zmienna do unikania mrugania ekranu
int aktualnyStanEkranu = -1; // -1: brak, 0: menu, 1: trening, 2: rozlaczony

// Klasa obsługująca wiadomości przychodzące z PC (Pythona)
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { deviceConnected = true; };
    void onDisconnect(BLEServer* pServer) { deviceConnected = false; }
};

class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        String rxValue = String(pCharacteristic->getValue().c_str());
        if (rxValue.length() > 0) {
            if (rxValue.startsWith("START:")) {
                wTreningu = true;
                startTreninguMilis = millis();
                powtorzenia = 0;
            } else if (rxValue == "STOP") {
                wTreningu = false;
            } else if (rxValue.startsWith("COUNT:")) {
                powtorzenia = rxValue.substring(6).toInt();
            }
        }
    }
};

void setup() {
  Serial.begin(115200);
  
  pinMode(BTN_NEXT, INPUT_PULLUP);
  pinMode(BTN_SELECT, INPUT_PULLUP);

  // Inicjalizacja ekranu LilyGO
  tft.init();
  tft.setRotation(2);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawCentreString("Inicjalizacja", 64, 40, 2);
  tft.drawCentreString("BLE...", 64, 60, 2);

  // Inicjalizacja BLE
  BLEDevice::init("CyberTrener_TQT");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);
  pTxCharacteristic = pService->createCharacteristic(CHARACTERISTIC_UUID_TX, BLECharacteristic::PROPERTY_NOTIFY);
  pTxCharacteristic->addDescriptor(new BLE2902());

  BLECharacteristic *pRxCharacteristic = pService->createCharacteristic(CHARACTERISTIC_UUID_RX, BLECharacteristic::PROPERTY_WRITE);
  pRxCharacteristic->setCallbacks(new MyCallbacks());

  pService->start();
  pServer->getAdvertising()->start();
}

void odswiezEkran() {
  int nowyStan = 0; // Domyślnie menu
  if (!deviceConnected) nowyStan = 2; // Rozłączony
  else if (wTreningu) nowyStan = 1;   // W trakcie treningu

  // ==========================================
  // CZĘŚĆ 1: Zmiana widoku (Czyści ekran TYLKO gdy zmieniamy z menu na trening itp.)
  // ==========================================
  if (nowyStan != aktualnyStanEkranu) {
    tft.fillScreen(TFT_BLACK); // Wywołane tylko raz na zmianę widoku! (Brak mrugania)
    aktualnyStanEkranu = nowyStan;

    if (aktualnyStanEkranu == 2) {
      tft.setTextColor(TFT_RED, TFT_BLACK);
      tft.drawCentreString("Rozlaczono", 64, 40, 2);
      tft.drawCentreString("z PC", 64, 65, 2);
    } 
    else if (aktualnyStanEkranu == 0) {
      tft.setTextColor(TFT_CYAN, TFT_BLACK);
      tft.drawCentreString("CYBER TRENER", 64, 30, 2);
      tft.setTextColor(TFT_WHITE, TFT_BLACK);
      tft.drawCentreString("Gotowy / Menu", 64, 70, 2);
    } 
    else if (aktualnyStanEkranu == 1) {
      // Rysujemy "etykiety" tylko raz
      tft.setTextColor(TFT_GREEN, TFT_BLACK);
      tft.drawCentreString("TRENING", 64, 2, 2);
      
      tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
      tft.drawCentreString("Czas:", 64, 25, 2);
      
      tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
      tft.drawCentreString("Powtorzenia:", 64, 75, 2);
    }
  }

  // ==========================================
  // CZĘŚĆ 2: Aktualizacja na bieżąco
  // ==========================================
  if (aktualnyStanEkranu == 1) {
    // Odświeżanie czasu
    unsigned long sekundy = (millis() - startTreninguMilis) / 1000;
    char timerBuf[16];
    sprintf(timerBuf, " %02lu:%02lu ", sekundy / 60, sekundy % 60); // Spacje zapobiegają śmieciom graficznym
    
    tft.setTextColor(TFT_WHITE, TFT_BLACK); 
    tft.drawCentreString(timerBuf, 64, 45, 4); // Duża czcionka, na środku ekranu (y=45)

    // Odświeżanie liczby powtórzeń
    char powtBuf[16];
    sprintf(powtBuf, "  %d  ", powtorzenia);
    
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawCentreString(powtBuf, 64, 95, 4); // Duża czcionka, na środku (y=95)
  }
}

void loop() {
  static unsigned long ostatniEkran = 0;
  if (millis() - ostatniEkran > 200) { 
    odswiezEkran();
    ostatniEkran = millis();
  }

  if (!deviceConnected) return;

  // 1. Lewy przycisk (NEXT)
  if (digitalRead(BTN_NEXT) == LOW) {
    pTxCharacteristic->setValue("NEXT");
    pTxCharacteristic->notify();
    delay(250); 
  }

  // 2. Prawy przycisk (SELECT / BACK)
  if (digitalRead(BTN_SELECT) == LOW) {
    if (!isSelectPressed) {
      btnSelectPressTime = millis();
      isSelectPressed = true;
    }
  } else {
    if (isSelectPressed) {
      unsigned long pressDuration = millis() - btnSelectPressTime;
      if (pressDuration > 800) {
        pTxCharacteristic->setValue("BACK");
      } else if (pressDuration > 50) {
        pTxCharacteristic->setValue("SELECT");
      }
      pTxCharacteristic->notify();
      isSelectPressed = false;
      delay(150);
    }
  }
}