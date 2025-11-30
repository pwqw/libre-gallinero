import math

LATITUDE = -32.5
LONGITUDE = -60  # Aproximado para Uruguay

# Calcular amanecer y atardecer (fórmula simplificada)
def calc_sun_times(year, month, day, latitude=LATITUDE, longitude=LONGITUDE):
    # Algoritmo simplificado, precisión suficiente para automatización
    Jday = 367*year - int((7*(year+int((month+9)/12)))/4) + int((275*month)/9) + day + 1721013.5
    n = Jday - 2451545.0 + 0.0008
    Jstar = n - (longitude/360)
    M = (357.5291 + 0.98560028 * Jstar) % 360
    C = 1.9148*math.sin(math.radians(M)) + 0.02*math.sin(math.radians(2*M)) + 0.0003*math.sin(math.radians(3*M))
    lambda_sun = (M + 102.9372 + C + 180) % 360
    Jtransit = 2451545.0 + Jstar + 0.0053*math.sin(math.radians(M)) - 0.0069*math.sin(math.radians(2*lambda_sun))
    delta = math.asin(math.sin(math.radians(lambda_sun))*math.sin(math.radians(23.44)))
    H = math.acos((math.sin(math.radians(-0.83)) - math.sin(math.radians(latitude))*math.sin(delta)) / (math.cos(math.radians(latitude))*math.cos(delta)))
    Jrise = Jtransit - H/(2*math.pi)
    Jset = Jtransit + H/(2*math.pi)
    def jd_to_hm(jd, longitude):
        # Convertir JD a fecha/hora UTC
        Z = int(jd)
        F = jd - Z
        if Z < 2299161:
            A = Z
        else:
            alpha = int((Z - 1867216.25)/36524.25)
            A = Z + 1 + alpha - int(alpha/4)
        B = A + 1524
        C = int((B - 122.1)/365.25)
        D = int(365.25 * C)
        E = int((B - D)/30.6001)
        day = B - D - int(30.6001 * E) + F
        frac_day = day - int(day)
        hours = int(frac_day * 24)
        minutes = int((frac_day * 24 - hours) * 60)
        # Calcular timezone desde longitud
        import timezone as tz_module
        tz_offset = tz_module.get_timezone_offset(longitude)
        # Ajustar por zona horaria
        hours = (hours + tz_offset) % 24
        return hours, minutes
    sunrise = jd_to_hm(Jrise, longitude)
    sunset = jd_to_hm(Jset, longitude)
    return sunrise, sunset


