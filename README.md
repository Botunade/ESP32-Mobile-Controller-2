# Tank Ultra-Console (MicroPython Edition)

A complete, single-file PID Tank Controller for ESP32 running MicroPython. This project replaces legacy C++ firmware with a unified Python application that handles hardware control, PID logic, and serves a modern Web Dashboard.

## Features

- **PID Control**: Precise variable output for proportional actuators.
- **Hybrid Control**: Optional Deadband (Hysteresis) logic for safety (Start/Stop limits).
- **Precision Calibration**: Configure Min/Max Voltage output for your specific actuator.
- **Web Dashboard**: Embedded, single-page application hosted directly on the ESP32.
  - Real-time graphing with Setpoint indicator.
  - Live configuration of PID, Geometry, and Limits.
  - Pump and Actuator status monitoring.
- **Hardware Interlock**: Actuator output is forced to 0V if the Pump is disabled by safety limits.

## Hardware Setup (ESP32)

| Component | ESP32 Pin | Type | Notes |
|-----------|-----------|------|-------|
| **Actuator** | GPIO 26 | Analog/PWM | 0-3.3V Output (Filtered PWM) |
| **Pump** | GPIO 16 | Digital Out | Relay Control |
| **Ultrasonic Trig** | GPIO 5 | Digital Out | HC-SR04 Trigger |
| **Ultrasonic Echo** | GPIO 18 | Digital In | HC-SR04 Echo |
| **Status LED** | GPIO 2 | Digital Out | Built-in LED |

## Getting Started

1. **Flash MicroPython**: Ensure your ESP32 is running the latest MicroPython firmware.
2. **Upload Code**: Upload `main.py` to the root of the ESP32 filesystem.
3. **Power On**: The device will create a WiFi Access Point.
4. **Connect**:
   - **SSID**: `TankController-AP`
   - **Password**: `tankwater`
5. **Dashboard**: Open `http://192.168.4.1` in your browser.

## Configuration Guide

### 1. Tank Geometry
Configure the physical dimensions of your tank to ensure accurate % readings.
- **Tank Height**: Total height of the water column (0-100%).
- **Empty Distance**: Distance from the sensor to the bottom of the tank (or 0% level).

### 2. Control Logic
- **Target Setpoint**: The desired water level %.
- **Deadband (Safety)**:
  - **Enable Switch**: Toggles safety limits.
  - **Stop Limit**: If level > limit, Pump & Actuator force OFF.
  - **Start Limit**: If level < limit, Pump enables (PID takes over).

### 3. Actuator Tuning
- **PID Gains**: Tune Kp, Ki, Kd for stability.
- **Voltage Calibration**:
  - **Min (V)**: Voltage output at 0% PID demand.
  - **Max (V)**: Voltage output at 100% PID demand.

## Development

### Running Tests
The project includes a test suite that runs on standard Python (PC) using mocks.

```bash
# Run unit tests
python3 tests/test_main.py
```

### File Structure
- `main.py`: The core application (Firmware + Web Server + UI).
- `tests/`: Unit tests and mocks.
