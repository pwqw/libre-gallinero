# ntp.py - NTP sync w/timezone
import logger
def log(msg):
 logger.log('ntp',msg)
def sync_ntp(longitude=None):
    import ntptime,utime,time
    log("=== NTP ===")
    tz_offset=0
    if longitude is not None:
        import timezone as tz_module
        tz_offset=int(tz_module.get_timezone_offset(longitude))
        log(f"TZ: UTC{tz_offset:+d}")
    try:
        tm=utime.localtime()
        log(f"Pre:{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}")
    except:pass
    for i in range(5):
        try:
            log(f"NTP {i+1}/5")
            ntptime.settime()
            if tz_offset!=0:
                import machine
                rtc=machine.RTC()
                ct=utime.time()
                at=ct+(tz_offset*3600)
                rtc.datetime(utime.localtime(at))
            try:
                tm=utime.localtime()
                log(f"Post:{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}")
                log(f"{tm[2]:02d}/{tm[1]:02d}/{tm[0]}")
            except:pass
            log("✓ NTP OK")
            return True
        except Exception as e:
            log(f"✗ NTP {i+1}/5:{e}")
            if i<4:time.sleep(2)
    log("✗ NTP FAIL")
    return False

