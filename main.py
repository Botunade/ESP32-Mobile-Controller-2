import time
try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

from lib.config import Config
from lib.wifi import WiFiManager
from lib.sensor import DistanceSensor
from lib.control import PumpController
from lib.ble import BLEManager
from lib.web import WebServer
import json

# Global instances
cfg = Config()
wifi = WiFiManager(cfg.get('wifi_ssid'), cfg.get('wifi_pass'))
sensor = DistanceSensor(cfg.get('trig_pin'), cfg.get('echo_pin'))
pump = PumpController(cfg.get('pump_pin'))
ble = BLEManager()

# Global state
state = {
    "level_percent": 0.0,
    "setpoint_percent": cfg.get('setpoint'),
    "lower_limit": cfg.get('lower_limit'),
    "pump_on": False,
    "distance_cm": 0.0
}

def get_status():
    # Helper for Web/BLE
    return {
        "level_percent": state["level_percent"],
        "setpoint_percent": cfg.get('setpoint'),
        "lower_limit": cfg.get('lower_limit'),
        "pump_on": pump.get_status()
    }

def ble_write_callback(data_str):
    try:
        data = json.loads(data_str)
        cfg.update(data)
        print("Updated config via BLE:", data)
    except Exception as e:
        print("BLE Write Error:", e)

async def sensor_loop():
    while True:
        # Measure
        dist = sensor.measure_cm()
        state["distance_cm"] = dist

        # Calculate percent
        # If dist <= min_dist, 100%
        # If dist >= max_dist, 0%
        # Actually it's inverted usually.
        # "Tank Height" is usually sensor to bottom.
        # "Empty Dist" (Max Distance) is sensor to empty water level.
        # "Min Distance" is sensor to full water level.

        min_d = cfg.get('min_distance_cm')
        max_d = cfg.get('max_distance_cm')

        if dist < 0:
            # Error
            state["level_percent"] = -1
        else:
            if max_d - min_d == 0:
                 percent = 0
            else:
                # Linear mapping
                # dist = min_d -> 100%
                # dist = max_d -> 0%
                percent = 100.0 * (max_d - dist) / (max_d - min_d)

            # Clamp
            if percent > 100: percent = 100
            if percent < 0: percent = 0

            state["level_percent"] = percent

        # Control Pump
        pump.update(state["level_percent"], cfg.get('setpoint'), cfg.get('lower_limit'))
        state["pump_on"] = pump.get_status()

        await asyncio.sleep(1)

async def ble_loop():
    while True:
        ble.send_status(get_status())
        await asyncio.sleep(1) # Notify every second

async def main():
    print("Starting Tank Controller...")

    # Start WiFi
    wifi.start_ap()

    # Setup BLE Callback
    ble.set_write_callback(ble_write_callback)

    # Web Server
    web = WebServer(cfg, pump, get_status)
    # Start server is async, we create task
    asyncio.create_task(web.start())

    # Loops
    asyncio.create_task(sensor_loop())
    asyncio.create_task(ble_loop())

    while True:
        await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
    except Exception as e:
        print("Error:", e)
