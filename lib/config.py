import json
import os

class Config:
    def __init__(self, filepath='config.json'):
        self.filepath = filepath
        self.config = {
            "setpoint": 80,
            "lower_limit": 40,
            "tank_height_cm": 200,
            "min_distance_cm": 0,
            "max_distance_cm": 200,
            "pump_pin": 23,
            "trig_pin": 5,
            "echo_pin": 18,
            "wifi_ssid": "TankController-AP",
            "wifi_pass": "tankwater"
        }
        self.load()

    def load(self):
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                self.config.update(data)
        except (OSError, ValueError):
            print("Config file not found or invalid, using defaults")
            # We don't necessarily want to overwrite immediately if read failed,
            # but for simplicity we ensure a valid file exists.
            self.save()

    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.config, f)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def update(self, new_config):
        for k, v in new_config.items():
            if k in self.config:
                self.config[k] = v
        self.save()
