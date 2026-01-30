import socket
import json
import time
import gc

try:
    import network
    import machine
    from machine import Pin, PWM
except ImportError:
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
ACTUATOR_PIN_NUM = 26 # Analog/PWM Control Voltage
PUMP_PIN_NUM = 16     # Digital Pump Control
LED_PIN_NUM = 2

DEFAULT_CONFIG = {
    # Geometry
    "tank_height": 200.0,
    "max_dist": 180.0,
    # Control
    "target_setpoint": 50.0,
    "deadband_enabled": True, # Default enabled for safety
    "stop_level": 90.0,
    "start_level": 10.0,
    # PID
    "kp": 1.0,
    "ki": 0.1,
    "kd": 0.0,
    # Output
    "dac_offset_v": 0.66,    # Offset Voltage
    "dac_max_v": 3.3,        # Max System Voltage
    "valve_max_duty": 1023   # PWM Resolution
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
        if dt <= 0: dt = 0.1

        error = self.setpoint - input_val

        # P
        p_term = self.kp * error

        # I
        self._integral += error * dt
        if self._integral * self.ki > self.out_max: self._integral = self.out_max / self.ki if self.ki else 0
        elif self._integral * self.ki < self.out_min: self._integral = self.out_min / self.ki if self.ki else 0
        i_term = self.ki * self._integral

        # D
        derivative = (error - self._last_error) / dt
        d_term = self.kd * derivative

        output = p_term + i_term + d_term

        if output < self.out_min: output = self.out_min
        elif output > self.out_max: output = self.out_max

        self._last_error = error
        self._last_time = current_time
        return output

# ==========================================
# CONTROLLER LOGIC
# ==========================================
class TankController:
    def __init__(self, config=DEFAULT_CONFIG):
        self.config = config.copy()

        try:
            self.trig = Pin(TRIG_PIN_NUM, Pin.OUT)
            self.echo = Pin(ECHO_PIN_NUM, Pin.IN)
            self.actuator = PWM(Pin(ACTUATOR_PIN_NUM), freq=1000)
            self.pump = Pin(PUMP_PIN_NUM, Pin.OUT)
            self.led = Pin(LED_PIN_NUM, Pin.OUT)

            self.actuator.duty(0)
            self.pump.value(0)
            self.led.value(0)
        except:
            print("Hardware init failed (Simulating)")
            self.trig = None
            self.actuator = None
            self.pump = None
            self.led = None

        self.pid = PID(0,0,0,0)

        self.level_percent = 0.0
        self.valve_percent = 0.0 # PID Output 0-100
        self.actuator_voltage = 0.0 # Actual Voltage
        self.pump_on = False
        self.simulated_level = 50.0
        self.pump_active_latch = False

    def read_distance(self):
        if self.trig is None:
            # Sim logic
            # Filling depends on Actuator Voltage? Or Valve %?
            # Let's say Valve % represents flow rate potential.
            # Pump must be ON for flow.

            flow_potential = self.valve_percent / 100.0
            if not self.pump_on: flow_potential = 0

            fill_rate = flow_potential * 1.5
            drain_rate = 0.5
            self.simulated_level += (fill_rate - drain_rate)
            if self.simulated_level < 0: self.simulated_level = 0
            if self.simulated_level > 100: self.simulated_level = 100

            h = self.config['tank_height']
            empty = self.config['max_dist']
            full_dist = empty - h
            if full_dist < 0: full_dist = 0

            span = empty - full_dist
            dist = empty - (self.simulated_level / 100.0 * span)
            return dist
        return 0

    def update(self):
        # 1. Config
        self.pid.update_params(self.config['kp'], self.config['ki'], self.config['kd'])
        self.pid.setpoint = self.config['target_setpoint']

        # 2. Input
        dist = self.read_distance()
        h = self.config['tank_height']
        empty = self.config['max_dist']
        full = empty - h
        span = empty - full
        if span <= 0: span = 1

        level_cm = empty - dist
        self.level_percent = (level_cm / span) * 100.0
        if self.level_percent < 0: self.level_percent = 0
        if self.level_percent > 100: self.level_percent = 100

        # 3. Deadband (Pump Logic)
        if self.config['deadband_enabled']:
            if self.level_percent >= self.config['stop_level']:
                self.pump_active_latch = False
            elif self.level_percent <= self.config['start_level']:
                self.pump_active_latch = True
            self.pump_on = self.pump_active_latch
        else:
            # If Deadband Disabled, Pump is Always Active?
            # Or manual control? Assuming Always Active for PID to work.
            self.pump_on = True

        # 4. PID Calc (Actuator)
        pid_out = self.pid.compute(self.level_percent)
        self.valve_percent = pid_out

        # 5. Output Logic
        # Calculate Target Voltage
        # V = Offset + (PID% * (Max - Offset))
        offset = self.config['dac_offset_v']
        max_v = self.config['dac_max_v']

        if self.pump_on:
             # Scale PID (0-100) to (Offset-MaxV)
             voltage_span = max_v - offset
             if voltage_span < 0: voltage_span = 0
             self.actuator_voltage = offset + (self.valve_percent / 100.0 * voltage_span)
        else:
             # If Pump is OFF, Force Actuator 0V (or Offset?)
             # "Force the pin to be zero" was for Pump pin.
             # Reasonable to set Actuator to 0V if system is off.
             self.actuator_voltage = 0.0

        # Clamp
        if self.actuator_voltage > max_v: self.actuator_voltage = max_v
        if self.actuator_voltage < 0: self.actuator_voltage = 0

        # Apply to Hardware
        if self.pump:
            self.pump.value(1 if self.pump_on else 0)

        if self.actuator:
            # Map Voltage to Duty
            # Duty = (V / MaxV) * Resolution
            if max_v > 0:
                duty_fraction = self.actuator_voltage / max_v
            else:
                duty_fraction = 0

            duty_res = self.config.get('valve_max_duty', 1023)
            duty = int(duty_fraction * duty_res)
            self.actuator.duty(duty)

        if self.led:
            self.led.value(1 if self.pump_on else 0)

# ==========================================
# HTML CONTENT
# ==========================================
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Tank Ultra-Console</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --bg: #06080c; --accent: #22d3ee; --accent-glow: rgba(34, 211, 238, 0.4); --card-bg: rgba(15, 23, 42, 0.85); --card-border: rgba(255, 255, 255, 0.06); --text: #ffffff; --text-muted: #64748b; --success: #10b981; --danger: #f43f5e; --warning: #fbbf24; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding: 24px 16px; min-height: 100vh; }
        .container { max-width: 500px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 24px; }
        h1 { font-size: 2.2rem; margin: 0; font-weight: 700; background: linear-gradient(135deg, #fff 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .status-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(15, 23, 42, 0.6); border: 1px solid var(--card-border); padding: 6px 16px; border-radius: 100px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-top: 12px; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--danger); box-shadow: 0 0 10px var(--danger); }
        .status-dot.online { background: var(--success); box-shadow: 0 0 10px var(--success); }
        .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 24px; padding: 24px; margin-bottom: 16px; }
        .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
        .metric-card { background: rgba(255, 255, 255, 0.02); border: 1px solid var(--card-border); border-radius: 20px; padding: 16px; text-align: center; }
        .metric-label { color: var(--text-muted); font-size: 0.65rem; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; }
        .metric-value { font-size: 2rem; font-weight: 700; line-height: 1; }
        .metric-unit { font-size: 0.9rem; color: var(--text-muted); font-weight: 400; }
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .section-title { font-size: 1rem; font-weight: 700; display: flex; align-items: center; gap: 8px; }
        .live-tag { font-size: 0.6rem; background: var(--accent); color: #000; padding: 2px 8px; border-radius: 100px; font-weight: 800; text-transform: uppercase; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
        .input-group { margin-bottom: 12px; }
        .label { display: block; color: var(--text-muted); font-size: 0.7rem; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; }
        input { width: 100%; background: rgba(0, 0, 0, 0.4); border: 1px solid var(--card-border); border-radius: 12px; padding: 12px; color: #fff; font-size: 1rem; font-weight: 600; text-align: center; border: 1px solid #334155; }
        button { width: 100%; background: var(--accent); color: #000; border: none; border-radius: 16px; padding: 14px; font-size: 0.9rem; font-weight: 700; cursor: pointer; text-transform: uppercase; margin-top: 8px; }
        button.secondary { background: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid var(--card-border); }
        button.danger { background: rgba(244, 63, 94, 0.1); color: var(--danger); border: 1px solid rgba(244, 63, 94, 0.2); }
        .active-config { margin-top: 16px; padding: 12px; background: rgba(0, 0, 0, 0.2); border-radius: 16px; font-size: 0.75rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 6px; }
        .config-row { display: flex; justify-content: space-between; }
        .config-value { color: var(--accent); font-weight: 700; }
        .chart-container { height: 160px; margin: 12px -8px 0 -8px; }
        footer { text-align: center; padding: 24px 0 40px; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; }

        .switch { position: relative; display: inline-block; width: 40px; height: 20px; }
        .switch input { opacity: 0; width: 0; height: 0; position: absolute; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #334155; transition: .4s; border-radius: 20px; }
        .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 2px; bottom: 2px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: var(--accent); }
        input:checked + .slider:before { transform: translateX(20px); }
        .toggle-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Tank Ultra</h1>
            <div class="status-badge">
                <div class="status-dot" id="dot"></div>
                <span id="stTxt">System Offline</span>
            </div>
        </header>

        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Water Level</div>
                <div class="metric-value" id="lvl">--<span class="metric-unit">%</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Actuator Voltage</div>
                <div class="metric-value" id="volt" style="font-size: 1.5rem;">--V</div>
            </div>
        </div>

        <div class="card" style="padding: 16px;">
            <div class="metric-label">Real-time Stream</div>
            <div class="chart-container"><canvas id="chart"></canvas></div>
        </div>

        <div class="card">
            <div class="section-header"><div class="section-title">Actuator Setpoint <span class="live-tag">PID Target</span></div></div>
            <div class="input-group"><label class="label">Target Level (%)</label><input type="number" id="inTarget" placeholder="50"></div>
            <button id="btnTarget">Set Target Point</button>
            <div class="active-config"><div class="config-row"><span>Active Target:</span><span class="config-value" id="valTarget">--%</span></div></div>
        </div>

        <div class="card">
            <div class="section-header"><div class="section-title">Pump Deadband <span class="live-tag">Safety</span></div></div>

            <div class="toggle-row">
                <label class="label" style="margin:0;">Enable Deadband</label>
                <label class="switch"><input type="checkbox" id="chkDeadband"><span class="slider"></span></label>
            </div>

            <div class="form-grid">
                <div class="input-group"><label class="label">Stop Limit (%)</label><input type="number" id="inStop" placeholder="90"></div>
                <div class="input-group"><label class="label">Start Limit (%)</label><input type="number" id="inStart" placeholder="10"></div>
            </div>
            <button class="secondary" id="btnPump">Apply Deadband</button>
            <div class="active-config">
                <div class="config-row"><span>Start/Stop:</span><span class="config-value" id="valPump">-- / --%</span></div>
                <div class="config-row"><span>Pump Status:</span><span class="config-value" id="valPumpStatus">--</span></div>
            </div>
        </div>

        <div class="card">
            <div class="section-header"><div class="section-title">Hardware Profile <span class="live-tag">Tank</span></div></div>
            <div class="form-grid">
                <div class="input-group"><label class="label">Tank Total (cm)</label><input type="number" id="inH" placeholder="200"></div>
                <div class="input-group"><label class="label">Empty Dist (cm)</label><input type="number" id="inM" placeholder="180"></div>
            </div>
            <button class="secondary" id="btnHw">Sync Geometry</button>
            <div class="active-config">
                <div class="config-row"><span>Total Height:</span><span class="config-value" id="valH">-- cm</span></div>
                <div class="config-row"><span>Empty Sensor:</span><span class="config-value" id="valM">-- cm</span></div>
            </div>
        </div>

        <div class="card">
            <div class="section-header"><div class="section-title">Actuator Tuning <span class="live-tag">PID/DAC</span></div></div>
            <div class="form-grid">
                <div class="input-group"><label class="label">Kp</label><input type="number" id="inKp" step="0.1"></div>
                <div class="input-group"><label class="label">Ki</label><input type="number" id="inKi" step="0.01"></div>
                <div class="input-group"><label class="label">Kd</label><input type="number" id="inKd" step="0.01"></div>
                <div class="input-group"><label class="label">Offset (V)</label><input type="number" id="inOffset" step="0.01"></div>
            </div>
            <button class="secondary" id="btnTun">Update Tuning</button>
            <div class="active-config">
                <div class="config-row"><span>Gains [P/I/D]:</span><span class="config-value" id="valPid">--</span></div>
                <div class="config-row"><span>Offset:</span><span class="config-value" id="valOffset">--V</span></div>
            </div>
        </div>

        <footer>Tank Controller Pro • v2.2 • MicroPython</footer>
    </div>

    <script>
        const el = {
            dot: document.getElementById('dot'), st: document.getElementById('stTxt'),
            lvl: document.getElementById('lvl'), volt: document.getElementById('volt'),
            vTarget: document.getElementById('valTarget'), vPump: document.getElementById('valPump'), vPumpSt: document.getElementById('valPumpStatus'),
            vH: document.getElementById('valH'), vM: document.getElementById('valM'), vPid: document.getElementById('valPid'), vOffset: document.getElementById('valOffset'),
            iTarget: document.getElementById('inTarget'), iStop: document.getElementById('inStop'),
            iStart: document.getElementById('inStart'), iH: document.getElementById('inH'),
            iM: document.getElementById('inM'), iKp: document.getElementById('inKp'),
            iKi: document.getElementById('inKi'), iKd: document.getElementById('inKd'),
            iOffset: document.getElementById('inOffset'),
            chkDB: document.getElementById('chkDeadband')
        };

        const chart = new Chart(document.getElementById('chart').getContext('2d'), {
            type: 'line', data: { labels: Array(60).fill(''), datasets: [
                { label: 'Level', data: Array(60).fill(null), borderColor: '#22d3ee', borderWidth: 3, tension: 0.4, pointRadius: 0, fill: true, backgroundColor: 'rgba(34, 211, 238, 0.05)' },
                { label: 'Setpoint', data: Array(60).fill(null), borderColor: '#fbbf24', borderWidth: 2, borderDash: [5, 5], pointRadius: 0, fill: false }
            ]},
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.02)' }, ticks: { display: false } } }, animation: false }
        });

        async function postConfig(data) {
            try {
                await fetch('/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
                alert("Settings Saved");
            } catch(e) { alert("Save Failed"); }
        }

        async function sync() {
            try {
                const res = await fetch('/status');
                if(!res.ok) throw new Error();
                const d = await res.json();

                el.dot.classList.add('online');
                el.st.innerText = "System Online";
                el.st.style.color = "var(--success)";

                el.lvl.innerHTML = `${d.level_percent.toFixed(0)}<span class="metric-unit">%</span>`;
                el.volt.innerText = `${d.actuator_voltage.toFixed(2)}V`;

                el.vTarget.innerText = `${d.target_setpoint}%`;
                el.vPump.innerText = `${d.start_level}% - ${d.stop_level}% (${d.deadband_enabled ? 'ON' : 'OFF'})`;
                el.vPumpSt.innerText = d.pump_on ? "ACTIVE" : "STOPPED";
                el.vPumpSt.style.color = d.pump_on ? "var(--success)" : "var(--danger)";

                el.vH.innerText = `${d.tank_height} cm`;
                el.vM.innerText = `${d.max_dist} cm`;
                el.vPid.innerText = `[${d.kp}, ${d.ki}, ${d.kd}]`;
                el.vOffset.innerText = `${d.dac_offset_v}V`;

                if(document.activeElement !== el.chkDB) el.chkDB.checked = d.deadband_enabled;

                if(chart.data.datasets[0].data.length >= 60) {
                    chart.data.datasets[0].data.shift();
                    chart.data.datasets[1].data.shift();
                }
                chart.data.datasets[0].data.push(d.level_percent);
                chart.data.datasets[1].data.push(d.target_setpoint);
                chart.update('none');

            } catch(e) {
                el.dot.classList.remove('online');
                el.st.innerText = "Connection Lost";
                el.st.style.color = "var(--danger)";
            }
        }
        setInterval(sync, 1000);
        sync();

        el.chkDB.addEventListener('change', () => postConfig({ deadband_enabled: el.chkDB.checked }));

        document.getElementById('btnTarget').onclick = () => postConfig({ target_setpoint: parseFloat(el.iTarget.value) });
        document.getElementById('btnPump').onclick = () => postConfig({ stop_level: parseFloat(el.iStop.value), start_level: parseFloat(el.iStart.value) });
        document.getElementById('btnHw').onclick = () => postConfig({ tank_height: parseFloat(el.iH.value), max_dist: parseFloat(el.iM.value) });
        document.getElementById('btnTun').onclick = () => postConfig({
            kp: parseFloat(el.iKp.value), ki: parseFloat(el.iKi.value), kd: parseFloat(el.iKd.value),
            dac_offset_v: parseFloat(el.iOffset.value)
        });
    </script>
</body>
</html>
"""

# ==========================================
# SERVER
# ==========================================
def start_server(controller):
    try:
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=WIFI_SSID, password=WIFI_PASS)
    except: pass

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    s.setblocking(False)

    print("Ultra-Console Ready")

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
            except OSError: pass

            req_str = request.decode()
            if not req_str:
                conn.close()
                continue

            line = req_str.split('\n')[0]
            parts = line.split(' ')
            method = parts[0]
            path = parts[1] if len(parts) > 1 else '/'

            resp = ""
            ctype = "text/html"

            if path == '/' or path == '/index.html':
                resp = HTML_CONTENT
            elif path == '/status':
                ctype = "application/json"
                st = controller.config.copy()
                st.update({
                    "level_percent": controller.level_percent,
                    "valve_percent": controller.valve_percent,
                    "actuator_voltage": controller.actuator_voltage,
                    "pump_on": controller.pump_on
                })
                resp = json.dumps(st)
            elif path == '/config' and method == 'POST':
                try:
                    body = req_str.split('\r\n\r\n')[1]
                    data = json.loads(body)
                    for k,v in data.items():
                        if k in controller.config and v is not None:
                            controller.config[k] = v
                    resp = json.dumps({"status": "ok"})
                    ctype = "application/json"
                except:
                    resp = json.dumps({"status": "err"})

            conn.send('HTTP/1.1 200 OK\r\n'.encode())
            conn.send(f'Content-Type: {ctype}\r\n'.encode())
            conn.send('Connection: close\r\n\r\n'.encode())
            conn.send(resp.encode())
            conn.close()

        except OSError: pass
        time.sleep(0.05)

if __name__ == '__main__':
    ctrl = TankController()
    start_server(ctrl)
