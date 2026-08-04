"""
hebrew_calendar.py - חסימה לפי לוח יהודי
שומר הפתח v2.0

דורש: pip install hdate
אם לא מותקן — משתמש בחישוב ידני של שבת בלבד
"""
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


def _sun_times(lat: float, lon: float, date: datetime) -> tuple[datetime, datetime]:
    """
    מחשב זמן זריחה ושקיעה לתאריך ומיקום נתון.
    מחזיר (sunrise, sunset) כ-datetime.
    """
    try:
        import ephem
        obs = ephem.Observer()
        obs.lat  = str(lat)
        obs.lon  = str(lon)
        obs.date = date.strftime("%Y/%m/%d")
        obs.horizon = "-0:34"   # תקן refraction
        sun = ephem.Sun()
        sunrise = ephem.localtime(obs.next_rising(sun))
        sunset  = ephem.localtime(obs.next_setting(sun))
        return sunrise, sunset
    except ImportError:
        pass

    # fallback: חישוב פשוט (דיוק ±10 דקות)
    day_of_year = date.timetuple().tm_yday
    lat_r = math.radians(lat)
    decl  = math.radians(-23.45 * math.cos(math.radians(360/365 * (day_of_year + 10))))
    cos_h = (math.sin(math.radians(-0.83)) - math.sin(lat_r)*math.sin(decl)) / \
            (math.cos(lat_r)*math.cos(decl))
    cos_h = max(-1, min(1, cos_h))
    h = math.degrees(math.acos(cos_h))
    lon_corr = lon / 15
    noon = 12 - lon_corr
    sunrise_h = noon - h / 15
    sunset_h  = noon + h / 15
    base = date.replace(hour=0, minute=0, second=0, microsecond=0)
    sunrise = base + timedelta(hours=sunrise_h)
    sunset  = base + timedelta(hours=sunset_h)
    return sunrise, sunset


def _is_shabbat(dt: datetime) -> bool:
    return dt.weekday() == 4   # שישי (ישראלי: שישי = ערב שבת)


def is_blocked_shabbat_chag(
    lat: float = 31.7683,    # ירושלים כברירת מחדל
    lon: float = 35.2137,
    minutes_before: int = 40,
    minutes_after: int = 40,
) -> tuple[bool, str]:
    """
    בודק אם עכשיו זמן חסימה לפי שבת/חג יהודי.
    מחזיר (is_blocked, reason).
    """
    now = datetime.now()
    weekday = now.weekday()   # 0=ב, ..., 4=ו, 5=ש, 6=א

    try:
        _, sunset_today = _sun_times(lat, lon, now)
        _, sunset_yesterday = _sun_times(lat, lon, now - timedelta(days=1))
    except Exception as e:
        logger.warning(f"חישוב שקיעה נכשל: {e}")
        return False, ""

    # ── ערב שבת / ערב חג (יום שישי) ──
    if weekday == 4:  # שישי
        shabbat_start = sunset_today - timedelta(minutes=minutes_before)
        if now >= shabbat_start:
            return True, f"שבת — כניסה בשעה {shabbat_start.strftime('%H:%M')}"

    # ── שבת עצמה ──
    if weekday == 5:  # שבת
        motzash = sunset_today + timedelta(minutes=minutes_after)
        if now < motzash:
            return True, f"שבת — יציאה בשעה {motzash.strftime('%H:%M')}"

    # ── חגים (מנסה hdate) ──
    try:
        import hdate
        hd = hdate.HDate(datetime=now)
        # בדוק אם היום יש חג
        holiday = hd.holiday_name
        if holiday:
            # ערב חג — מחר חג?
            tomorrow = hdate.HDate(datetime=now + timedelta(days=1))
            if tomorrow.holiday_name:
                chag_start = sunset_today - timedelta(minutes=minutes_before)
                if now >= chag_start:
                    return True, f"ערב {tomorrow.holiday_name}"
            # חג היום
            motz_chag = sunset_today + timedelta(minutes=minutes_after)
            if now < motz_chag:
                return True, f"חג {holiday}"
    except ImportError:
        pass   # hdate לא מותקן — שבת בלבד
    except Exception as e:
        logger.debug(f"hdate שגיאה: {e}")

    return False, ""
