try:
    import network
except ImportError:
    network = None
import time

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.ap = None
        if network:
            self.ap = network.WLAN(network.AP_IF)

    def start_ap(self):
        if not self.ap:
            print(f"Mock AP started: SSID={self.ssid}, IP=192.168.4.1")
            return

        self.ap.active(True)
        # authmode=3 is WPA2-PSK
        self.ap.config(essid=self.ssid, password=self.password, authmode=3)

        # Wait for active
        retries = 0
        while not self.ap.active():
            time.sleep(0.1)
            retries += 1
            if retries > 50:
                print("Failed to activate AP")
                return

        print('AP started')
        print(self.ap.ifconfig())
