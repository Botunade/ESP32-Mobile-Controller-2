import time
try:
    import machine
except ImportError:
    machine = None # For testing/linting outside ESP32

class DistanceSensor:
    def __init__(self, trig_pin, echo_pin):
        if machine:
            self.trig = machine.Pin(trig_pin, machine.Pin.OUT)
            self.echo = machine.Pin(echo_pin, machine.Pin.IN)
            self.trig.value(0)
        else:
            print(f"Mock Sensor initialized on Trig={trig_pin}, Echo={echo_pin}")

    def measure_cm(self):
        if not machine:
            return 50.0 # Mock value

        self.trig.value(0)
        time.sleep_us(2)
        self.trig.value(1)
        time.sleep_us(10)
        self.trig.value(0)

        try:
            # timeout 30000us = 30ms. Max distance ~5m.
            pulse_time = machine.time_pulse_us(self.echo, 1, 30000)
        except OSError:
             return -1

        if pulse_time < 0:
            return -1

        # Speed of sound is 343 m/s or 0.0343 cm/us
        # Distance = (pulse_time * 0.0343) / 2
        distance = (pulse_time * 0.0343) / 2
        return distance
