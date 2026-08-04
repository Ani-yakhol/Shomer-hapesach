"""
app_monitor.py - ניטור תוכנות פעילות
Computer Guardian - שומר המחשב
"""

import subprocess
import threading
import time
import ctypes
import logging

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil לא מותקן - ניטור אפליקציות מוגבל")


def get_running_processes() -> list[str]:
    """מחזיר רשימת שמות תהליכים רצים"""
    if HAS_PSUTIL:
        try:
            return [p.name().lower() for p in psutil.process_iter(["name"])]
        except Exception:
            pass
    # גיבוי ב-tasklist
    try:
        out = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/nh"],
            text=True, creationflags=0x08000000
        )
        names = []
        for line in out.strip().split("\n"):
            parts = line.strip().strip('"').split('","')
            if parts:
                names.append(parts[0].lower())
        return names
    except Exception:
        return []


def get_foreground_app() -> str | None:
    """מחזיר שם תהליך החלון הפעיל"""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if HAS_PSUTIL:
            try:
                p = psutil.Process(pid.value)
                return p.name().lower()
            except Exception:
                pass
        return None
    except Exception:
        return None


def kill_process(process_name: str) -> bool:
    """סוגר תהליך לפי שם"""
    if HAS_PSUTIL:
        killed = False
        for p in psutil.process_iter(["name"]):
            try:
                if p.name().lower() == process_name.lower():
                    p.terminate()
                    killed = True
            except Exception:
                pass
        return killed
    try:
        subprocess.call(
            ["taskkill", "/f", "/im", process_name],
            creationflags=0x08000000
        )
        return True
    except Exception:
        return False


class AppMonitor:
    """
    ניטור תוכנות פעילות.
    - מצב קיוסק: סוגר כל תוכנה שאינה ברשימה המאושרת
    - מעקב זמן לתוכנות מוגבלות
    - מזהה את האפליקציה הפעילה בחזית ומעדכן את TimeManager
    """

    def __init__(self, config_manager, username: str, time_manager=None):
        self.cm          = config_manager
        self.username    = username
        self.tm          = time_manager
        self._running    = False
        self._thread     = None
        self._interval   = 2.0   # שניות בין בדיקות

        self.on_app_change  = None  # callback(app_name: str | None)
        self.on_blocked_app = None  # callback(app_name: str)
        self.on_app_expired = None  # callback(app_name: str)

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="AppMonitor", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        last_fg = None
        while self._running:
            try:
                user = self.cm.get_user(self.username)
                if not user:
                    time.sleep(self._interval)
                    continue

                # זיהוי חלון פעיל
                fg = get_foreground_app()
                if fg != last_fg:
                    last_fg = fg
                    if self.tm:
                        self.tm.set_current_app(fg)
                    if self.on_app_change:
                        self.on_app_change(fg)

                # מצב קיוסק - חסימת תוכנות לא מאושרות
                allowed = user.get("allowed_apps")
                if allowed is not None and fg:
                    allowed_lower = [a.lower() for a in allowed]
                    if fg.lower() not in allowed_lower:
                        # תוכנה לא מאושרת - סגור אותה
                        kill_process(fg)
                        if self.on_blocked_app:
                            self.on_blocked_app(fg)

            except Exception as e:
                logger.error(f"שגיאה ב-AppMonitor: {e}")

            time.sleep(self._interval)

    def get_restricted_apps_running(self) -> list[str]:
        """מחזיר רשימת תוכנות מוגבלות שכרגע רצות"""
        user = self.cm.get_user(self.username)
        if not user:
            return []
        app_limits = user.get("app_limits", {})
        if not app_limits:
            return []
        running = get_running_processes()
        found = []
        for limited_name in app_limits:
            for proc in running:
                if limited_name.lower() in proc.lower():
                    found.append(proc)
                    break
        return found
