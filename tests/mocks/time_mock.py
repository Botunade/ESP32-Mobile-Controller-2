# Add missing time functions for testing
import time

if not hasattr(time, 'ticks_ms'):
    def ticks_ms():
        return int(time.time() * 1000)
    time.ticks_ms = ticks_ms

if not hasattr(time, 'ticks_diff'):
    def ticks_diff(start, end):
        return start - end
    time.ticks_diff = ticks_diff

if not hasattr(time, 'sleep_us'):
    def sleep_us(us):
        time.sleep(us / 1000000.0)
    time.sleep_us = sleep_us
