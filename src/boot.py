# boot.py - Minimal bootstrap (MicroPython best practices)
# Only essential system initialization

try:
    import gc
    gc.collect()
except:
    pass

try:
    import webrepl
    webrepl.start()
    print("[boot] WebREPL started on :8266")
except Exception as e:
    print("[boot] WebREPL error:", e)
