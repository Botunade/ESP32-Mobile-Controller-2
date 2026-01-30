import sys
import os
import unittest
import json
import time

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'tests/mocks'))

import machine
import network
import main

class TestTankController(unittest.TestCase):
    def setUp(self):
        self.ctrl = main.TankController()
        # Mock hardware
        self.ctrl.trig = None
        self.ctrl.valve = machine.PWM(machine.Pin(4))

        # Reset config
        self.ctrl.config.update({
            "tank_height": 100.0,
            "max_dist": 100.0,
            "target_setpoint": 50.0,
            "stop_level": 90.0,
            "start_level": 10.0,
            "kp": 1.0, "ki": 0.0, "kd": 0.0,
            "deadband_enabled": False
        })
        self.ctrl.simulated_level = 50.0
        self.ctrl.valve_percent = 0.0

    def test_pid_basic(self):
        self.ctrl.config['deadband_enabled'] = False
        self.ctrl.read_distance = lambda: 60.0 # 40%
        self.ctrl.update()
        # Error 10 -> Output 10
        self.assertAlmostEqual(self.ctrl.valve_percent, 10.0, places=1)

    def test_deadband_disabled_safety_only(self):
        # Even with deadband disabled, the original code had a safety stop?
        # Re-reading main.py logic:
        # if self.config['deadband_enabled']:
        #    ... hysteresis logic ...
        # else:
        #    self.valve_percent = pid_out

        # So if Disabled, PID runs ALWAYS, even above Stop Level (90).
        # Assuming PID Setpoint is 50, and Level is 95.
        # Error -45. Output clamped to 0.
        # But what if Setpoint is 95 and Level is 95? Error 0.
        # What if Setpoint is 100 (Full) and Level is 99? Error 1. Output 1.
        # If Deadband Enabled, and Stop Level is 90, it should be OFF even if Setpoint is 100.

        self.ctrl.config['target_setpoint'] = 100.0
        self.ctrl.config['stop_level'] = 90.0
        self.ctrl.config['deadband_enabled'] = False
        self.ctrl.read_distance = lambda: 5.0 # 95%

        self.ctrl.update()

        # Error = 5. Output = 5. Since Deadband Disabled, we expect 5.
        self.assertAlmostEqual(self.ctrl.valve_percent, 5.0, places=1)

    def test_deadband_enabled_logic(self):
        self.ctrl.config['target_setpoint'] = 100.0
        self.ctrl.config['stop_level'] = 90.0
        self.ctrl.config['start_level'] = 20.0
        self.ctrl.config['deadband_enabled'] = True

        # 1. Start High (95%) -> Should be OFF
        self.ctrl.read_distance = lambda: 5.0 # 95%
        self.ctrl.update()
        self.assertEqual(self.ctrl.valve_percent, 0.0)
        self.assertFalse(self.ctrl.pump_active_latch)

        # 2. Drop to 50% -> Still OFF (Latched)
        self.ctrl.read_distance = lambda: 50.0 # 50%
        self.ctrl.update()
        self.assertEqual(self.ctrl.valve_percent, 0.0)

        # 3. Drop below Start (10%) -> Turn ON
        self.ctrl.read_distance = lambda: 90.0 # 10%
        self.ctrl.update()
        self.assertTrue(self.ctrl.pump_active_latch)
        # Error = 100 - 10 = 90. Output 90.
        self.assertAlmostEqual(self.ctrl.valve_percent, 90.0, places=1)

        # 4. Rise to 50% -> Still ON (Latched)
        self.ctrl.read_distance = lambda: 50.0 # 50%
        self.ctrl.update()
        self.assertTrue(self.ctrl.pump_active_latch)
        # Error = 50. Output 50.
        self.assertAlmostEqual(self.ctrl.valve_percent, 50.0, places=1)

if __name__ == '__main__':
    unittest.main()
