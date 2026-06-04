import asyncio
import threading
from bleak import BleakScanner, BleakClient

# ==========================================
# GŁÓWNE UUID DLA USŁUGI UART (Zgodne z kodem ESP32)
# ==========================================
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"


class BleManager:
    def __init__(self, command_callback):
        self.ble_client = None
        self.callback = command_callback
        self.running = True

        # --- Asynchroniczna pętla dla Bluetooth ---
        # Odpalamy jako demon, żeby nie blokował zamknięcia aplikacji głównej
        self.ble_loop = asyncio.new_event_loop()
        threading.Thread(target=self.ble_loop.run_forever, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self.connect_ble(), self.ble_loop)

    async def connect_ble(self):
        print("Szukanie urządzenia CyberTrener_TQT...")
        device = await BleakScanner.find_device_by_name("CyberTrener_TQT", timeout=10.0)
        if not device:
            print("Nie znaleziono kostki LilyGO przez BLE. Sprawdź zasilanie ESP32.")
            return

        async with BleakClient(device) as client:
            self.ble_client = client
            print("Połączono z LilyGO przez Bluetooth!")

            def notification_handler(sender, data):
                # Dekodujemy komendę przychodzącą z ESP32
                cmd = data.decode('utf-8').strip()
                self.callback(cmd)

            await client.start_notify(TX_CHAR_UUID, notification_handler)

            # Podtrzymanie pętli dopóki aplikacja działa i urządzenie jest połączone
            while self.running and client.is_connected:
                await asyncio.sleep(0.5)

    def send_to_esp(self, msg):
        # Wysyłanie sygnałów do ESP32 (np. wystartowanie wibracji lub licznika)
        if self.ble_client and self.ble_client.is_connected:
            asyncio.run_coroutine_threadsafe(
                self.ble_client.write_gatt_char(RX_CHAR_UUID, msg.encode()),
                self.ble_loop
            )