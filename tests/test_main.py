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
            "dac_offset_v": 0.5,
            "dac_max_v": 3.0
        })
        self.ctrl.simulated_level = 50.0
        self.ctrl.valve_percent = 0.0
        # Initialize pump state
        self.ctrl.pump_active_latch = True
        self.ctrl.pump_on = True

    def test_pid_with_offset(self):
        # We need to ensure Pump is ON for Actuator to be ON
        # Pump Logic uses Deadband. Level 40 is between Start(10) and Stop(90).
        # We initialized latch to True.

        # Setpoint 50, Level 40 -> Error 10 -> PID 10%
        self.ctrl.read_distance = lambda: 60.0 # 40%
        self.ctrl.update()

        # Check Pump State
        self.assertTrue(self.ctrl.pump_on, "Pump should be ON")

        # Voltage Calc: Offset + (PID% * (Max - Offset))
        # 0.5 + (0.10 * (3.0 - 0.5))
        # 0.5 + (0.10 * 2.5) = 0.5 + 0.25 = 0.75V

        self.assertAlmostEqual(self.ctrl.valve_percent, 10.0, places=1)
        self.assertAlmostEqual(self.ctrl.actuator_voltage, 0.75, places=2)

    def test_pump_interlock(self):
        self.ctrl.config['target_setpoint'] = 100.0
        self.ctrl.config['stop_level'] = 90.0

        # Level 95% -> Exceeds Stop -> Pump OFF
        self.ctrl.read_distance = lambda: 5.0 # 95%
        self.ctrl.update()

        self.assertFalse(self.ctrl.pump_on)
        self.assertEqual(self.ctrl.actuator_voltage, 0.0)

    def test_offset_config_change(self):
        new_cfg = {"dac_offset_v": 1.0}
        self.ctrl.config.update(new_cfg)

        # Ensure Level is within bounds to keep pump ON
        self.ctrl.read_distance = lambda: 50.0 # 50%
        self.ctrl.update()

        self.assertTrue(self.ctrl.pump_on)
        self.assertAlmostEqual(self.ctrl.actuator_voltage, 1.0, places=2)

if __name__ == '__main__':
    unittest.main()
