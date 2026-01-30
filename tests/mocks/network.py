STA_IF = 0
AP_IF = 1

class WLAN:
    def __init__(self, interface_id):
        self.interface_id = interface_id
        self.active_ = False
        self.status_ = 0
        self.ifconfig_ = ('0.0.0.0', '0.0.0.0', '0.0.0.0', '0.0.0.0')

    def active(self, is_active=None):
        if is_active is not None:
            self.active_ = is_active
        return self.active_

    def connect(self, ssid, password):
        pass

    def isconnected(self):
        return True

    def ifconfig(self, config=None):
        if config:
            self.ifconfig_ = config
        return self.ifconfig_

    def config(self, **kwargs):
        pass
