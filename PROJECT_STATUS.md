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
- **Local Access**: Hosted directly on the ESP32. Access via: **[http://192.168.4.1](http://192.168.4.1)** (When connected to `TankController-AP`).
- **Features**:
  - Real-time Graphing with Setpoint Indicator.
  - Live Telemetry: Water Level %, Actuator Voltage, Pump Status.
  - Configuration: Target Setpoint, PID Tuning (Kp, Ki, Kd), Voltage Calibration (Min/Max), Geometry (Height/Dist).
  - Controls: Deadband Toggle, Manual Sync buttons.

## 📂 Project Structure & Development Guide

### Core (Production)
- **`main.py`**: The **ONLY** file required to run the device. It contains:
  - **Firmware Logic**: `TankController` class, `PID` class, Hardware Drivers.
  - **Web Server**: Non-blocking socket server implementation.
  - **Frontend**: Embedded HTML/CSS/JS for the Web Dashboard.

### Testing Infrastructure (Development Only)
These files are used to verify the code logic on a computer *before* uploading to the ESP32. They are **not** needed on the device itself.

- **`tests/test_main.py`**: The Unit Test Suite.
  - **Purpose**: Verifies that the PID math is correct, the logic for switching the Pump ON/OFF works, and that configuration updates are handled properly.
  - **Why use it?**: It allows finding bugs in logic (e.g., "Does the pump turn off when the tank is full?") instantly without needing to flash the chip and wire up sensors.

- **`tests/mocks/`**: Hardware Simulation Modules.
  - **Purpose**: Standard Python (on a PC) doesn't know what `import machine` or `import network` means. These files "pretend" to be the ESP32 hardware so `main.py` can run during tests.
  - **`machine.py`**: Simulates Pins, PWM, and Pulse timing. It allows the test to say "Set Pin 4 High" and verify it happened.
  - **`network.py`**: Simulates the WiFi interface logic.
  - **`time_mock.py`**: Adds MicroPython-specific timing functions (`ticks_ms`) to standard Python's `time` module.

## 🔧 Hardware Pinout (ESP32)

| Component | Pin | Type | Function |
|-----------|-----|------|----------|
| **Actuator** | 26 | Analog/PWM | Proportional Valve Control (0-3.3V) |
| **Pump** | 16 | Digital | On/Off Control (Interlocked) |
| **Trig** | 5 | Digital | Ultrasonic Trigger |
| **Echo** | 18 | Digital | Ultrasonic Echo |
| **LED** | 2 | Digital | Status Indicator |
