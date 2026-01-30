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
        self.ctrl.config['tank_height_cm'] = 100.0
        self.ctrl.config['min_distance_cm'] = 0.0
        self.ctrl.config['max_distance_cm'] = 100.0
        self.ctrl.config['setpoint'] = 50.0
        self.ctrl.config['kp'] = 1.0
        self.ctrl.config['ki'] = 0.0
        self.ctrl.config['kd'] = 0.0

        self.ctrl.simulated_level = 50.0
        self.ctrl.valve_percent = 0.0

    def test_pid_proportional(self):
        self.ctrl.config['setpoint'] = 50.0
        self.ctrl.config['kp'] = 1.0
        self.ctrl.config['ki'] = 0.0
        self.ctrl.config['kd'] = 0.0

        def mock_read_distance():
            return 60.0
        self.ctrl.read_distance = mock_read_distance

        self.ctrl.update()

        self.assertAlmostEqual(self.ctrl.level_percent, 40.0)
        self.assertAlmostEqual(self.ctrl.valve_percent, 10.0, places=1)

    def test_pid_response_direction(self):
        self.ctrl.config['setpoint'] = 50.0
        self.ctrl.read_distance = lambda: 20.0 # 80% level
        self.ctrl.update()
        self.assertEqual(self.ctrl.valve_percent, 0.0)

    def test_simulation_process(self):
        self.ctrl = main.TankController()
        self.ctrl.trig = None

        self.ctrl.simulated_level = 50.0
        self.ctrl.config['setpoint'] = 80.0
        self.ctrl.config['kp'] = 2.0
        self.ctrl.config['ki'] = 0.0
        self.ctrl.config['kd'] = 0.0

        # First Update
        # Initial Valve=0. Drain=0.5. Level becomes 49.5.
        # Error = 30.5. Output = 61.0.
        self.ctrl.update()
        self.assertAlmostEqual(self.ctrl.valve_percent, 61.0, places=1)

        # Next Update:
        # Valve=61.0.
        # Fill Rate = 61/100 * 2 = 1.22.
        # Drain Rate = 0.5.
        # Net = +0.72.
        # New Level approx 49.5 + 0.72 = 50.22.
        old_level = self.ctrl.simulated_level # 49.5
        self.ctrl.update()
        self.assertTrue(self.ctrl.simulated_level > old_level)

if __name__ == '__main__':
    unittest.main()
