try:
    import ubluetooth
except ImportError:
    ubluetooth = None
import json
import struct

class BLEManager:
    def __init__(self, name="Tank Controller BLE"):
        self.ble = None
        self.name = name
        self.connected_conn_handle = None
        self.write_callback = None

        if ubluetooth:
            self.ble = ubluetooth.BLE()
            self.ble.active(True)
            self.ble.irq(self.ble_irq)

            # Define UUIDs
            self.service_uuid = ubluetooth.UUID("4fafc201-1fb5-459e-8fcc-c5c9c331914b")
            self.status_uuid = ubluetooth.UUID("beb5483e-36e1-4688-b7f5-ea07361b26a8")
            self.control_uuid = ubluetooth.UUID("885f8386-3532-4048-8167-25e21508246d")

            # Register Service
            self.service = (
                self.service_uuid,
                (
                    (self.status_uuid, ubluetooth.FLAG_NOTIFY | ubluetooth.FLAG_READ),
                    (self.control_uuid, ubluetooth.FLAG_WRITE),
                ),
            )
            self.services = (self.service,)

            ((self.status_handle, self.control_handle),) = self.ble.gatts_register_services(self.services)

            self.advertise()
        else:
            print("Mock BLE initialized")

    def advertise(self):
        if not self.ble: return
        # Advertising payload
        # Flag: 0x01 (Flags) -> 0x06 (LE General Discoverable Mode, BR/EDR Not Supported)
        # Name: 0x09 (Complete Local Name)

        payload = bytearray()

        # Flags
        payload.append(2) # Length
        payload.append(0x01) # Type
        payload.append(0x06) # Value

        # Name
        name_bytes = self.name.encode('utf-8')
        payload.append(len(name_bytes) + 1)
        payload.append(0x09)
        payload.extend(name_bytes)

        # Service UUID (Complete 128-bit Service UUIDs) - 0x07
        # This is getting long, might exceed packet size.
        # Standard packet is 31 bytes.
        # 3 (flags) + len(name) + 2 (name header).
        # Tank Controller BLE is 19 chars. Total ~24 bytes. Fits.

        self.ble.gap_advertise(100, payload)

    def ble_irq(self, event, data):
        # Constants from micropython docs
        _IRQ_CENTRAL_CONNECT = 1
        _IRQ_CENTRAL_DISCONNECT = 2
        _IRQ_GATTS_WRITE = 3

        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self.connected_conn_handle = conn_handle
            print("BLE Connected")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self.connected_conn_handle = None
            print("BLE Disconnected")
            self.advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if conn_handle == self.connected_conn_handle and value_handle == self.control_handle:
                # Read the data
                data = self.ble.gatts_read(self.control_handle)
                if self.write_callback:
                    # decode utf-8
                    try:
                        str_data = data.decode('utf-8')
                        self.write_callback(str_data)
                    except:
                        pass

    def send_status(self, data):
        if self.connected_conn_handle is not None and self.ble:
             json_data = json.dumps(data)
             try:
                self.ble.gatts_notify(self.connected_conn_handle, self.status_handle, json_data)
             except Exception as e:
                 print("BLE Notify Error:", e)

    def set_write_callback(self, callback):
        self.write_callback = callback
