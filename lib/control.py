try:
    import machine
except ImportError:
    machine = None

class PumpController:
    def __init__(self, pin):
        if machine:
            self.pin = machine.Pin(pin, machine.Pin.OUT)
            self.pin.value(0) # Start OFF
        else:
            print(f"Mock Pump initialized on Pin={pin}")
        self.is_running = False

    def update(self, level_percent, setpoint, lower_limit):
        # Hysteresis Logic for Filling Tank
        # Start if level <= lower_limit (Low level start)
        # Stop if level >= setpoint (High level stop)

        if level_percent is None or level_percent < 0:
            # Error reading sensor, safety stop
            self.stop()
            return

        if level_percent >= setpoint:
            self.stop()
        elif level_percent <= lower_limit:
            self.start()

        # If in between, keep current state.

    def start(self):
        if not self.is_running:
            self.is_running = True
            if machine:
                self.pin.value(1) # Assumption: Active HIGH
            # print("Pump STARTED")

    def stop(self):
        if self.is_running:
            self.is_running = False
            if machine:
                self.pin.value(0)
            # print("Pump STOPPED")

    def get_status(self):
        return self.is_running
