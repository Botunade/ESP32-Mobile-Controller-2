# Water Level Controller

ESP32-based water tank level monitoring and control system with PID regulation and wireless API.

## Features

- **Ultrasonic Level Sensing** - HC-SR04 sensor for accurate water level measurement
- **PID Control** - Automatic valve regulation to maintain desired water level
- **WiFi Access Point** - Built-in AP mode for wireless connectivity
- **REST API** - JSON-based API for monitoring and configuration
- **Real-time Telemetry** - Live water level, valve position, and PID parameters
- **Web/Mobile Compatible** - CORS-enabled for browser and mobile app access

## Hardware Requirements

### Components
- ESP32-DEV board
- HC-SR04 ultrasonic distance sensor
- 4-20mA valve controller
- DAC output circuit (for valve control)
- Power supply (5V for ESP32, appropriate voltage for valve)

### Wiring

| Component | ESP32 Pin | Notes |
|-----------|-----------|-------|
| Ultrasonic TRIG | GPIO 5 | Trigger pin |
| Ultrasonic ECHO | GPIO 18 | Echo pin |
| Valve DAC Output | GPIO 25 | 0-3.3V output (4-20mA) |

## Software Setup

### 1. Install PlatformIO

```bash
# Install PlatformIO Core
pip install platformio

# Or use PlatformIO IDE extension for VS Code
```

### 2. Configure Hardware

Edit `include/config.h` to match your setup:

```cpp
// Tank dimensions (in centimeters)
#define TANK_HEIGHT_CM   200.0f  // Your tank height
#define MIN_DISTANCE_CM  3.0f    // Sensor to water when full
#define MAX_DISTANCE_CM  200.0f  // Sensor to water when empty

// WiFi credentials
#define AP_SSID     "TankController-AP"
#define AP_PASSWORD "tankwater"

// PID tuning (adjust for your system)
#define DEFAULT_KP 2.0f
#define DEFAULT_KI 0.5f
#define DEFAULT_KD 0.1f
```

### 3. Build and Upload

```bash
# Build the firmware
pio run

# Upload to ESP32
pio run --target upload

# Monitor serial output
pio device monitor
```

## API Endpoints

### GET /
Get system information and status.

**Response:**
```json
{
  "name": "ESP32 Tank Controller",
  "version": "0.2.0",
  "ip": "192.168.4.1",
  "ssid": "TankController-AP",
  "status": "ok"
}
```

### GET /status
Get current telemetry data.

**Response:**
```json
{
  "level_percent": 65.5,
  "setpoint_percent": 60.0,
  "kp": 2.0,
  "ki": 0.5,
  "kd": 0.1,
  "valve_percent": 45.2,
  "control_voltage": 1.85,
  "timestamp_ms": 123456
}
```

### POST /pid
Update PID parameters and setpoint.

**Request:**
```json
{
  "setpoint": 70.0,
  "kp": 2.5,
  "ki": 0.6,
  "kd": 0.15
}
```

**Response:**
```json
{
  "status": "updated",
  "setpoint_percent": 70.0,
  "kp": 2.5,
  "ki": 0.6,
  "kd": 0.15
}
```

## Configuration

All configuration is centralized in `include/config.h`:

- **WiFi Settings** - AP SSID and password
- **Hardware Pins** - GPIO assignments
- **Tank Geometry** - Physical dimensions
- **PID Parameters** - Control loop tuning
- **Timing** - Update intervals

## Usage

### 1. Power On
- ESP32 starts WiFi AP automatically
- Default SSID: `TankController-AP`
- Default Password: `tankwater`
- Default IP: `192.168.4.1`

### 2. Connect
- Connect device to WiFi AP
- Access API at `http://192.168.4.1`

### 3. Monitor
- Use mobile app or web interface
- Or use curl:
```bash
curl http://192.168.4.1/status
```

### 4. Adjust Setpoint
```bash
curl -X POST http://192.168.4.1/pid \
  -H "Content-Type: application/json" \
  -d '{"setpoint": 75.0}'
```

## PID Tuning

The system uses a PID controller to maintain water level:

- **Kp (Proportional)** - Immediate response to error
- **Ki (Integral)** - Eliminates steady-state error
- **Kd (Derivative)** - Dampens oscillations

**Tuning Tips:**
1. Start with Kp only (Ki=0, Kd=0)
2. Increase Kp until oscillations occur
3. Add Ki to eliminate offset
4. Add Kd to reduce overshoot

## Troubleshooting

### WiFi AP Not Starting
- Check serial monitor for error messages
- Verify ESP32 has sufficient power
- System will auto-restart on AP failure

### Inaccurate Level Readings
- Verify sensor wiring (TRIG/ECHO pins)
- Check `MIN_DISTANCE_CM` and `MAX_DISTANCE_CM` in config
- Ensure sensor has clear line of sight to water
- Check for timeout messages in serial monitor

### Valve Not Responding
- Verify DAC pin connection (GPIO 25)
- Check valve power supply
- Monitor `control_voltage` in API response
- Should range from 0.66V (closed) to 3.30V (open)

### API Not Accessible
- Confirm connected to correct WiFi AP
- Check IP address in serial monitor
- Verify firewall settings on client device

## Development

### Project Structure
```
water-level-controller/
├── include/
│   └── config.h          # Configuration constants
├── src/
│   └── main.cpp          # Main firmware code
├── platformio.ini        # Build configuration
├── .gitignore
└── README.md
```

### Code Quality
```bash
# Run static analysis
pio check

# Clean build
pio run --target clean
pio run
```

## License

[Add your license here]

## Version History

- **0.2.0** - Externalized configuration, added error handling
- **0.1.0** - Initial release with basic PID control
