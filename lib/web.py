try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
import json

class WebServer:
    def __init__(self, config, pump, get_status_callback):
        self.config = config
        self.pump = pump
        self.get_status_callback = get_status_callback

    async def handle_client(self, reader, writer):
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return

            try:
                request_line = request_line.decode().strip()
                parts = request_line.split()
                if len(parts) < 2:
                    writer.close()
                    return
                method, path = parts[0], parts[1]
            except Exception:
                writer.close()
                return

            # Read headers
            headers = {}
            content_length = 0
            while True:
                line = await reader.readline()
                if not line or line == b'\r\n':
                    break
                try:
                    line_str = line.decode().strip()
                    if ': ' in line_str:
                        key, val = line_str.split(': ', 1)
                        headers[key.lower()] = val
                        if key.lower() == 'content-length':
                            content_length = int(val)
                except:
                    pass

            # Read Body
            body = ''
            if content_length > 0:
                body_bytes = await reader.read(content_length)
                body = body_bytes.decode()

            response = self.router(method, path, body)

            # CORS headers
            cors = "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n"

            header = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n{cors}\r\n"
            writer.write(header.encode())
            writer.write(response.encode())
            await writer.drain()
            writer.close()

        except Exception as e:
            print("Web Error:", e)
            try:
                writer.close()
            except:
                pass

    def router(self, method, path, body):
        if method == 'OPTIONS':
            return ""

        if method == 'GET':
            if path == '/' or path == '/info':
                return json.dumps({"name": "Tank Controller", "version": "1.0"})
            elif path == '/status':
                return json.dumps(self.get_status_callback())
            elif path == '/config':
                return json.dumps(self.config.config)

        if method == 'POST':
            data = {}
            try:
                data = json.loads(body)
            except:
                pass

            if path == '/pid':
                if 'setpoint' in data: self.config.set('setpoint', data['setpoint'])
                if 'lower_limit' in data: self.config.set('lower_limit', data['lower_limit'])
                return json.dumps({"status": "ok"})
            elif path == '/config':
                self.config.update(data)
                return json.dumps({"status": "ok"})

        return json.dumps({"error": "not found"})

    async def start(self):
        print("Starting Web Server on port 80...")
        try:
            await asyncio.start_server(self.handle_client, '0.0.0.0', 80)
        except Exception as e:
            print("Failed to start server:", e)
