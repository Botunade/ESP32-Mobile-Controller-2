import sys
import os
import unittest
import json
import time

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'tests/mocks'))

import time_mock # Patch time module for ticks_ms
import machine
import network
import main

class TestTankController(unittest.TestCase):
    def setUp(self):
        self.ctrl = main.TankController()
        # Mock hardware
        self.ctrl.trig = None
        self.ctrl.actuator = machine.PWM(machine.Pin(26))
        self.ctrl.pump = machine.Pin(16)

        # Reset config
        self.ctrl.config.update({
            "tank_height": 100.0,
            "max_dist": 100.0,
            "target_setpoint": 50.0,
            "stop_level": 90.0,
            "start_level": 10.0,
            "kp": 1.0, "ki": 0.0, "kd": 0.0,
            "deadband_enabled": True,
            "dac_min_v": 0.5,
            "dac_max_v": 3.0
        })
        self.ctrl.simulated_level = 50.0
        self.ctrl.valve_percent = 0.0
        self.ctrl.pump_active_latch = True
        self.ctrl.pump_on = True

    def test_voltage_scaling(self):
        # Min=0.5, Max=3.0, Span=2.5

        # 0% PID -> Min Voltage
        self.ctrl.valve_percent = 0.0
        self.ctrl.pump_on = True
        self.ctrl.update() # Will recalc voltage based on PID (Wait, update() recalcs PID!)
        # So we must manipulate PID input (level) to get 0% or 100%.

        # Setpoint 50. Level 50. Error 0. PID 0.
        self.ctrl.read_distance = lambda: 50.0 # 50%
        self.ctrl.update()
        self.assertAlmostEqual(self.ctrl.actuator_voltage, 0.5, places=2)

        # Setpoint 50. Level 40. Error 10. PID 10.
        # Voltage = 0.5 + (0.1 * 2.5) = 0.75
        self.ctrl.read_distance = lambda: 60.0 # 40%
        self.ctrl.update()
        self.assertAlmostEqual(self.ctrl.actuator_voltage, 0.75, places=2)

        # Setpoint 50. Level 0. Error 50. PID 50.
        # Voltage = 0.5 + (0.5 * 2.5) = 0.5 + 1.25 = 1.75
        self.ctrl.read_distance = lambda: 100.0 # 0%
        self.ctrl.update()
        self.assertAlmostEqual(self.ctrl.actuator_voltage, 1.75, places=2)

    def test_calibration_update(self):
        # Update calibration to Min=1.0, Max=2.0 (Span=1.0)
        self.ctrl.config.update({"dac_min_v": 1.0, "dac_max_v": 2.0})

        # Setpoint 50. Level 0. Error 50. PID 50.
        # Voltage = 1.0 + (0.5 * 1.0) = 1.5
        self.ctrl.read_distance = lambda: 100.0 # 0%
        self.ctrl.update()
        self.assertAlmostEqual(self.ctrl.actuator_voltage, 1.5, places=2)

if __name__ == '__main__':
    unittest.main()
