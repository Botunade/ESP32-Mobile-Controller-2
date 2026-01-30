# Tank Controller Project - Current Status

**Last Updated:** 2025-12-05

## ✅ Completed Tasks

### 1. Architecture Overhaul
- **Single-File Firmware**: Consolidated entire application (Logic + Web Server + UI) into `main.py` for MicroPython.
- **Legacy Cleanup**: Removed C++ firmware (`hardware-test`), legacy React Native app (`mobile-app`), and Electron app (`desktop-app`).
- **Bluetooth Removal**: Completely removed all BLE code, focusing on WiFi Access Point mode.

### 2. Control Logic Implementation
- **PID Controller**: Implemented robust PID algorithm (`PID` class) replacing simple hysteresis.
  - Features: Proportional, Integral, Derivative terms with Anti-Windup.
  - Precision Timing: Uses `time.ticks_ms()` for accurate `dt` calculation.
- **Hybrid Deadband**: Added optional Safety Hysteresis mode.
  - Logic: Gates the PID output. Forces Pump OFF if > Stop Limit. Forces Pump ON (PID Active) if < Start Limit.
- **Hardware Drivers**:
  - **Actuator**: PWM/DAC on Pin 26 with Precision Voltage Calibration (Min/Max V mapping).
  - **Pump**: Digital Control on Pin 16 with Safety Interlock (Actuator forced 0V if Pump OFF).
  - **Sensor**: HC-SR04 Driver on Pins 5 (Trig) / 18 (Echo).

### 3. User Interface (Web Dashboard)
- **Tank Ultra-Console**: Modern, dark-mode web dashboard embedded in `main.py`.
- **Features**:
  - Real-time Graphing with Setpoint Indicator.
  - Live Telemetry: Water Level %, Actuator Voltage, Pump Status.
  - Configuration: Target Setpoint, PID Tuning (Kp, Ki, Kd), Voltage Calibration (Min/Max), Geometry (Height/Dist).
  - Controls: Deadband Toggle, Manual Sync buttons.

## 📂 Project Structure Guide

### Core
- **`main.py`**: The heart of the project. This single file contains:
  - **Firmware Logic**: `TankController` class, `PID` class, Hardware Drivers.
  - **Web Server**: Non-blocking socket server implementation.
  - **Frontend**: Embedded HTML/CSS/JS for the Web Dashboard.

### Testing & Development
- **`tests/`**: Contains unit tests to verify logic without hardware.
  - **`test_main.py`**: The primary test suite. Verifies PID math, Voltage scaling logic, Deadband state transitions, and Config updates.
- **`tests/mocks/`**: Simulation modules to allow running MicroPython code on a standard PC.
  - **`machine.py`**: Mocks ESP32 hardware classes (`Pin`, `PWM`, `time_pulse_us`).
  - **`network.py`**: Mocks WiFi networking classes (`WLAN`).
  - **`time_mock.py`**: Polyfills MicroPython-specific time functions (`ticks_ms`, `ticks_diff`, `sleep_us`) for standard Python.

### Documentation
- **`README.md`**: User guide, Hardware Pinout, and Getting Started instructions.
- **`PROJECT_STATUS.md`**: This file. Tracks progress and architecture.

## 🔧 Hardware Pinout (ESP32)

| Component | Pin | Type | Function |
|-----------|-----|------|----------|
| **Actuator** | 26 | Analog/PWM | Proportional Valve Control (0-3.3V) |
| **Pump** | 16 | Digital | On/Off Control (Interlocked) |
| **Trig** | 5 | Digital | Ultrasonic Trigger |
| **Echo** | 18 | Digital | Ultrasonic Echo |
| **LED** | 2 | Digital | Status Indicator |
