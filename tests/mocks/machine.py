class Pin:
    OUT = 0
    IN = 1
    def __init__(self, id, mode=None, pull=None):
        self.id = id
        self.mode = mode
        self.value_ = 0
    def value(self, v=None):
        if v is not None:
            self.value_ = v
        return self.value_

class PWM:
    def __init__(self, pin, freq=0, duty=0):
        self.pin = pin
        self.freq_ = freq
        self.duty_ = duty
    def freq(self, f=None):
        if f is not None: self.freq_ = f
        return self.freq_
    def duty(self, d=None):
        if d is not None: self.duty_ = d
        return self.duty_

class ADC:
    ATTN_11DB = 3
    WIDTH_10BIT = 10
    def __init__(self, pin):
        self.pin = pin
    def read(self):
        return 0
    def atten(self, a): pass
    def width(self, w): pass

def reset():
    pass

def freq(f):
    pass
