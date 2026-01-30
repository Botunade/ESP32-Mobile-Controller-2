import socket
import json
import time
import gc

try:
    import network
    import machine
    from machine import Pin, PWM
except ImportError:
    # Fallback for testing on PC
    import sys
    import os
    try:
        import network
        import machine
        from machine import Pin, PWM
    except ImportError:
        pass

# ==========================================
# CONFIGURATION
# ==========================================
WIFI_SSID = 'TankController-AP'
WIFI_PASS = 'tankwater'

TRIG_PIN_NUM = 5
ECHO_PIN_NUM = 18
VALVE_PIN_NUM = 4  # PWM Output for Valve/Pump
LED_PIN_NUM = 2

DEFAULT_CONFIG = {
    "tank_height_cm": 200.0,
    "min_distance_cm": 20.0,
    "max_distance_cm": 180.0,
    "setpoint": 50.0,          # Target Level %
    "kp": 2.0,
    "ki": 0.1,
    "kd": 0.5,
    "valve_min_duty": 0,       # 0-65535
    "valve_max_duty": 65535
}

# ==========================================
# PID CONTROLLER
# ==========================================
class PID:
    def __init__(self, kp, ki, kd, setpoint, out_min=0, out_max=100):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.out_min = out_min
        self.out_max = out_max

        self._integral = 0
        self._last_error = 0
        self._last_time = time.time()

    def update_params(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def compute(self, input_val):
        current_time = time.time()
        dt = current_time - self._last_time
        if dt <= 0: dt = 0.1 # Prevent div/0 on first run or fast loops

        error = self.setpoint - input_val

        # Proportional
        p_term = self.kp * error

        # Integral
        self._integral += error * dt
        i_term = self.ki * self._integral

        # Derivative
        derivative = (error - self._last_error) / dt
        d_term = self.kd * derivative

        # Output
        output = p_term + i_term + d_term

        # Clamp
        if output < self.out_min:
            output = self.out_min
            # Anti-windup: clamp integral if we are hitting limits?
            # Simple anti-windup: stop growing integral if clamped
            self._integral -= error * dt
        elif output > self.out_max:
            output = self.out_max
            self._integral -= error * dt

        self._last_error = error
        self._last_time = current_time

        return output

# ==========================================
# HTML CONTENT
# ==========================================
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tank Controller</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --accent: #3b82f6; --success: #22c55e; --danger: #ef4444; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); padding: 20px; max-width: 600px; margin: 0 auto; -webkit-font-smoothing: antialiased; }
        h1 { font-size: 1.5rem; margin-bottom: 0.5rem; text-align: center; }
        .subtitle { text-align: center; color: #94a3b8; margin-bottom: 2rem; font-size: 0.9rem; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
        .card { background: var(--card); padding: 16px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .full-width { grid-column: span 2; }
        .label { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; display: block; }
        .value { font-size: 1.5rem; font-weight: 700; }
        .unit { font-size: 0.9rem; color: #64748b; font-weight: 400; }
        button { background: var(--accent); color: white; border: none; padding: 14px; border-radius: 12px; font-weight: 600; font-size: 1rem; cursor: pointer; width: 100%; transition: opacity 0.2s; margin-bottom: 10px; }
        button:active { opacity: 0.8; }
        button:disabled { background: #334155; color: #94a3b8; cursor: not-allowed; opacity: 1; }
        button.danger { background: var(--danger); }
        input { background: #020617; border: 1px solid #334155; color: white; padding: 12px; border-radius: 8px; width: 100%; font-size: 1.1rem; box-sizing: border-box; text-align: center; margin-bottom: 10px; }
        .chart-container { height: 250px; width: 100%; margin-top: 10px; }
        .hidden { display: none !important; }
        .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #64748b; margin-right: 6px; }
        .connected .status-dot { background: var(--success); box-shadow: 0 0 8px var(--success); }
    </style>
</head>
<body>
    <h1>Tank Controller</h1>
    <p class="subtitle">PID Edition</p>

    <div id="statusPanel" class="card mb-4 text-center" style="margin-bottom: 20px;">
        <div style="margin-bottom: 10px;">
            <div id="statusIndicator" class="status-dot"></div>
            <span id="statusText" style="color: #94a3b8; font-size: 0.9rem;">Connecting...</span>
        </div>
    </div>

    <div id="dashboard" class="hidden">
        <div class="grid">
            <div class="card">
                <span class="label">Water Level</span>
                <div class="value" id="levelDisplay">-- <span class="unit">%</span></div>
            </div>
            <div class="card">
                <span class="label">Valve Output</span>
                <div class="value" id="valveDisplay">-- <span class="unit">%</span></div>
            </div>
        </div>

        <div class="card full-width">
            <span class="label">Performance</span>
            <div class="chart-container">
                <canvas id="levelChart"></canvas>
            </div>
        </div>

        <div class="card full-width">
            <span class="label">PID Control</span>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 10px; margin-top: 10px;">
                <div><label class="label">Target (%)</label><input type="number" id="targetInput" placeholder="50"></div>
                <div><label class="label">Kp</label><input type="number" id="kpInput" step="0.1"></div>
                <div><label class="label">Ki</label><input type="number" id="kiInput" step="0.01"></div>
                <div><label class="label">Kd</label><input type="number" id="kdInput" step="0.01"></div>
            </div>
            <button id="updateBtn" style="margin-top: 10px;">Update PID Parameters</button>
        </div>

        <button id="configBtn" style="background: #334155;">⚙️ Geometry Configuration</button>
    </div>

    <div id="configModal" class="hidden" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000;">
        <div style="background: var(--card); border-radius: 16px; padding: 20px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto;">
            <h2 style="margin-top: 0; margin-bottom: 20px;">Configuration</h2>
            <div style="margin-bottom: 20px;">
                <h3 style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 10px;">TANK GEOMETRY</h3>
                <div style="display: grid; gap: 10px;">
                    <div><label class="label">Tank Height (cm)</label><input type="number" id="cfg_tank_height" step="0.1"></div>
                    <div><label class="label">Min Distance (cm)</label><input type="number" id="cfg_min_distance" step="0.1"></div>
                    <div><label class="label">Max Distance (cm)</label><input type="number" id="cfg_max_distance" step="0.1"></div>
                </div>
            </div>
            <div style="display: flex; gap: 10px;">
                <button id="saveConfigBtn" style="flex: 1; background: var(--success);">💾 Save Configuration</button>
                <button id="closeConfigBtn" style="flex: 1; background: var(--danger);">✖ Cancel</button>
            </div>
        </div>
    </div>

    <script>
        const maxDataPoints = 60;
        let chart = null;

        const ui = {
            dashboard: document.getElementById('dashboard'),
            statusText: document.getElementById('statusText'),
            statusIndicator: document.getElementById('statusIndicator').parentElement,
            level: document.getElementById('levelDisplay'),
            valve: document.getElementById('valveDisplay'),
            targetInput: document.getElementById('targetInput'),
            kpInput: document.getElementById('kpInput'),
            kiInput: document.getElementById('kiInput'),
            kdInput: document.getElementById('kdInput'),
            updateBtn: document.getElementById('updateBtn')
        };

        const ctx = document.getElementById('levelChart').getContext('2d');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(maxDataPoints).fill(''),
                datasets: [{
                    label: 'Level %', data: Array(maxDataPoints).fill(null),
                    borderColor: '#22d3ee', backgroundColor: 'rgba(34, 211, 238, 0.1)',
                    borderWidth: 2, tension: 0.4, fill: true, pointRadius: 0
                }, {
                    label: 'Setpoint', data: Array(maxDataPoints).fill(null),
                    borderColor: '#ef4444', borderWidth: 1, borderDash: [5, 5], pointRadius: 0, fill: false
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { min: 0, max: 100, grid: { color: '#334155' } }, x: { display: false } },
                animation: false
            }
        });

        function setConnected(connected, msg) {
            ui.statusText.innerText = msg;
            if (connected) {
                ui.statusIndicator.classList.add('connected');
                ui.dashboard.classList.remove('hidden');
            } else {
                ui.statusIndicator.classList.remove('connected');
            }
        }

        function updateDashboard(data) {
            ui.level.innerHTML = `${data.level_percent.toFixed(1)} <span class="unit">%</span>`;
            ui.valve.innerHTML = `${data.valve_percent.toFixed(1)} <span class="unit">%</span>`;

            // Only update inputs if not focused (simple check)
            if (document.activeElement !== ui.targetInput) ui.targetInput.placeholder = data.setpoint;
            if (document.activeElement !== ui.kpInput) ui.kpInput.placeholder = data.kp;

            if (chart.data.labels.length >= maxDataPoints) {
                chart.data.datasets[0].data.shift();
                chart.data.datasets[1].data.shift();
            }
            chart.data.datasets[0].data.push(data.level_percent);
            chart.data.datasets[1].data.push(data.setpoint);
            chart.update('none');
        }

        async function pollStatus() {
            try {
                const res = await fetch('/status');
                if (!res.ok) throw new Error("Status failed");
                const data = await res.json();
                setConnected(true, "Connected");
                updateDashboard(data);
            } catch (e) {
                console.log("Poll fail", e);
                setConnected(false, "Disconnected / Polling...");
            }
        }

        setInterval(pollStatus, 1000);
        pollStatus();

        ui.updateBtn.addEventListener('click', async () => {
             const setpoint = parseFloat(ui.targetInput.value) || parseFloat(ui.targetInput.placeholder);
             const kp = parseFloat(ui.kpInput.value) || parseFloat(ui.kpInput.placeholder);
             const ki = parseFloat(ui.kiInput.value) || parseFloat(ui.kiInput.placeholder);
             const kd = parseFloat(ui.kdInput.value) || parseFloat(ui.kdInput.placeholder);

             ui.updateBtn.innerText = "Saving...";
             ui.updateBtn.disabled = true;

             try {
                 await fetch('/pid', {
                     method: 'POST',
                     headers: {'Content-Type': 'application/json'},
                     body: JSON.stringify({ setpoint, kp, ki, kd })
                 });
                 setTimeout(() => {
                     ui.updateBtn.innerText = "Update PID Parameters";
                     ui.updateBtn.disabled = false;
                     ui.targetInput.value = '';
                 }, 500);
             } catch (e) { alert("Update failed"); ui.updateBtn.disabled = false; }
        });

        const configModal = document.getElementById('configModal');
        document.getElementById('configBtn').addEventListener('click', async () => {
            try {
                const res = await fetch('/config');
                const data = await res.json();
                document.getElementById('cfg_tank_height').value = data.tank_height_cm || '';
                document.getElementById('cfg_min_distance').value = data.min_distance_cm || '';
                document.getElementById('cfg_max_distance').value = data.max_distance_cm || '';
                configModal.classList.remove('hidden');
            } catch (e) { alert("Failed to load config"); }
        });

        document.getElementById('closeConfigBtn').addEventListener('click', () => configModal.classList.add('hidden'));
        document.getElementById('saveConfigBtn').addEventListener('click', async () => {
            try {
                const payload = {
                    tank_height_cm: parseFloat(document.getElementById('cfg_tank_height').value),
                    min_distance_cm: parseFloat(document.getElementById('cfg_min_distance').value),
                    max_distance_cm: parseFloat(document.getElementById('cfg_max_distance').value)
                };
                await fetch('/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                alert('Configuration saved!');
                configModal.classList.add('hidden');
            } catch (e) { alert("Error saving config"); }
        });
    </script>
</body>
</html>
"""

# ==========================================
# CONTROLLER LOGIC
# ==========================================
class TankController:
    def __init__(self, config=DEFAULT_CONFIG):
        self.config = config.copy()

        # Hardware setup
        try:
            self.trig = Pin(TRIG_PIN_NUM, Pin.OUT)
            self.echo = Pin(ECHO_PIN_NUM, Pin.IN)
            # Use PWM for Valve Control (0-100% duty)
            self.valve = PWM(Pin(VALVE_PIN_NUM), freq=1000)
            self.led = Pin(LED_PIN_NUM, Pin.OUT)
            self.valve.duty(0) # Start closed
            self.led.value(0)
        except:
            print("Hardware init failed (Simulating)")
            self.trig = None
            self.echo = None
            self.valve = None
            self.led = None

        self.pid = PID(
            kp=self.config['kp'],
            ki=self.config['ki'],
            kd=self.config['kd'],
            setpoint=self.config['setpoint']
        )

        self.level_percent = 0.0
        self.valve_percent = 0.0
        self.simulated_level = 50.0

    def read_distance(self):
        if self.trig is None:
            # Simulation
            # Simple process model: Level increases if valve is open (Filling)
            # Rate of change proportional to Valve %
            fill_rate = (self.valve_percent / 100.0) * 2.0 # Max 2% per tick
            drain_rate = 0.5 # Constant drain 0.5% per tick

            self.simulated_level += (fill_rate - drain_rate)
            if self.simulated_level < 0: self.simulated_level = 0
            if self.simulated_level > 100: self.simulated_level = 100

            span = self.config['max_distance_cm'] - self.config['min_distance_cm']
            dist = self.config['max_distance_cm'] - (self.simulated_level / 100.0 * span)
            return dist

        # Real HC-SR04 reading would go here
        return 0

    def update(self):
        # 1. Read Process Variable (Level)
        current_dist = self.read_distance()
        max_d = self.config['max_distance_cm']
        min_d = self.config['min_distance_cm']
        span = max_d - min_d
        if span == 0: span = 1

        level_cm = max_d - current_dist
        self.level_percent = (level_cm / span) * 100.0
        if self.level_percent < 0: self.level_percent = 0
        if self.level_percent > 100: self.level_percent = 100

        # 2. Compute PID
        self.pid.setpoint = self.config['setpoint']
        self.pid.update_params(self.config['kp'], self.config['ki'], self.config['kd'])

        # Error = Setpoint - Level (Positive error means we need to Fill)
        # If Valve controls Filling, PID output corresponds to Valve %
        pid_out = self.pid.compute(self.level_percent)
        self.valve_percent = pid_out

        # 3. Drive Output
        if self.valve:
            # Map 0-100% to Duty Cycle
            # Use configuration for max duty cycle to support different resolutions (10-bit vs 16-bit)
            max_duty = self.config.get('valve_max_duty', 1023)
            duty_val = int((self.valve_percent / 100.0) * max_duty)
            self.valve.duty(duty_val)

        if self.led:
             # LED brightness proportional to valve
             self.led.value(1 if self.valve_percent > 5 else 0)

# ==========================================
# WEB SERVER
# ==========================================
def start_server(controller):
    try:
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=WIFI_SSID, password=WIFI_PASS)
        print("AP Active:", ap.ifconfig())
    except:
        print("WiFi Init Failed (Simulating)")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    s.setblocking(False)

    print("PID Server Listening on port 80")

    while True:
        controller.update()

        try:
            conn, addr = s.accept()
            conn.settimeout(0.5)
            request = b""
            try:
                while True:
                    chunk = conn.recv(1024)
                    if not chunk: break
                    request += chunk
                    if b"\r\n\r\n" in request or len(chunk) < 1024: break
            except OSError:
                pass

            req_str = request.decode()
            if not req_str:
                conn.close()
                continue

            first_line = req_str.split('\n')[0]
            method, path, _ = first_line.split(' ')

            response = ""
            content_type = "text/html"

            if path == '/' or path == '/index.html':
                response = HTML_CONTENT
            elif path == '/status':
                content_type = "application/json"
                response = json.dumps({
                    "level_percent": controller.level_percent,
                    "setpoint": controller.config['setpoint'],
                    "valve_percent": controller.valve_percent,
                    "kp": controller.config['kp'],
                    "ki": controller.config['ki'],
                    "kd": controller.config['kd']
                })
            elif path == '/config':
                if method == 'POST':
                    body = req_str.split('\r\n\r\n')[1]
                    try:
                        new_cfg = json.loads(body)
                        controller.config.update(new_cfg)
                        response = json.dumps({"status": "ok"})
                    except:
                        response = json.dumps({"status": "error"})
                else:
                    response = json.dumps(controller.config)
                content_type = "application/json"
            elif path == '/pid':
                 if method == 'POST':
                    body = req_str.split('\r\n\r\n')[1]
                    try:
                        data = json.loads(body)
                        if 'setpoint' in data: controller.config['setpoint'] = data['setpoint']
                        if 'kp' in data: controller.config['kp'] = data['kp']
                        if 'ki' in data: controller.config['ki'] = data['ki']
                        if 'kd' in data: controller.config['kd'] = data['kd']
                        response = json.dumps({"status": "ok"})
                    except:
                        response = json.dumps({"status": "error"})
                 content_type = "application/json"
            else:
                response = "Not Found"

            conn.send('HTTP/1.1 200 OK\r\n'.encode())
            conn.send(f'Content-Type: {content_type}\r\n'.encode())
            conn.send('Connection: close\r\n\r\n'.encode())
            conn.send(response.encode())
            conn.close()

        except OSError:
            pass

        time.sleep(0.05)

def main():
    ctrl = TankController()
    start_server(ctrl)

if __name__ == '__main__':
    main()
