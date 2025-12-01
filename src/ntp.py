# ntp.py - NTP sync w/timezone
import logger
def log(msg):
 logger.log('ntp',msg)

def sync_ntp(tz_offset=0):
    import ntptime,utime,time
    log("=== NTP ===")
    if tz_offset!=0:
        log(f"TZ:UTC{tz_offset:+d}")
    try:
        tm=utime.localtime()
        log(f"Pre:{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d} {tm[2]:02d}/{tm[1]:02d}/{tm[0]}")
    except:pass
    for i in range(5):
        try:
            log(f"NTP {i+1}/5")
            ntptime.settime()
            timestamp_utc=utime.time()
            if tz_offset!=0:
                timestamp_local=timestamp_utc+(tz_offset*3600)
                import machine
                rtc=machine.RTC()
                tm_local=utime.localtime(timestamp_local)
                rtc.datetime((tm_local[0],tm_local[1],tm_local[2],tm_local[6],tm_local[3],tm_local[4],tm_local[5],0))
            tm=utime.localtime()
            log(f"Local:{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d} {tm[2]:02d}/{tm[1]:02d}/{tm[0]}")
            tm_utc=utime.localtime(timestamp_utc)
            log(f"UTC:{tm_utc[3]:02d}:{tm_utc[4]:02d}:{tm_utc[5]:02d} {tm_utc[2]:02d}/{tm_utc[1]:02d}/{tm_utc[0]}")
            log("✓ OK")
            return (True,timestamp_utc)
        except Exception as e:
            log(f"✗ {i+1}/5:{e}")
            if i<4:time.sleep(2)
    log("✗ FAIL")
    return (False,0)
