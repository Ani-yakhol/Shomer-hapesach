"""
time_manager.py - ניהול זמן שימוש, ספירה והתראות
Computer Guardian - שומר המחשב
"""

import time
import threading
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class TimeManager(QObject):
    """
    מנהל זמן שימוש למשתמש.
    סופר שניות, מפעיל התראות, נועל בסיום הזמן.
    """

    # אותות
    tick            = pyqtSignal(int, object)  # (שניות שנוצלו, שניות שנותרו / None)
    warning_signal  = pyqtSignal(int)          # שניות שנותרו
    time_expired    = pyqtSignal()             # הזמן נגמר
    app_tick        = pyqtSignal(str, int, object)  # (שם אפליקציה, שניות שנוצלו, שנותרו)
    app_expired     = pyqtSignal(str)          # שם אפליקציה שהזמן נגמר

    def __init__(self, config_manager, username: str, parent=None):
        super().__init__(parent)
        self.cm         = config_manager
        self.username   = username
        self.user       = config_manager.get_user(username)

        self.session_start  = datetime.now()
        self.session_seconds = 0   # שניות מהכניסה הנוכחית
        self.daily_used      = config_manager.get_time_used_today(username)
        self._last_saved_at  = 0   # שניות שנשמרו לקובץ

        self._running   = False
        self._paused    = False
        self._timer     = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        # מעקב אחרי התראות שכבר נשלחו
        self._warned_at: set = set()

        # אפליקציות מוגבלות
        self._app_seconds: dict[str, int] = {}  # שם -> שניות שנוצלו
        self._current_app: str | None = None

    # ── הפעלה ועצירה ─────────────────────────────────────────────

    def start(self):
        self._running = True
        self._paused  = False
        self._timer.start()

    def pause(self):
        """עצירת ספירה — שומר את הזמן שנצבר עד כה"""
        if self._paused:
            return
        self._paused = True
        # שמירת שארית הזמן שלא נשמר (בין שמירת ה-60 שניות האחרונה לרגע הנוכחי)
        remainder = self.session_seconds % 60
        if remainder > 0:
            self.cm.add_time_used(self.username, remainder)
        self._last_saved_seconds = self.session_seconds

    def resume(self):
        """חידוש ספירה — לא מוסיף כפילויות"""
        if not self._paused:
            return
        self._paused = False
        # מאפס את ה-"שניות שנשמרו" כדי שהשמירה הבאה תהיה נכונה
        self._last_saved_at = self.session_seconds

    def stop(self):
        """עצירה מלאה — שמירת כל הזמן שנצבר"""
        self._running = False
        self._timer.stop()
        # שמור רק את מה שלא נשמר עדיין
        unsaved = self.session_seconds - getattr(self, '_last_saved_at', 0)
        if unsaved > 0:
            self.cm.add_time_used(self.username, unsaved)

    def elapsed_seconds(self) -> int:
        """מחזיר שניות שחלפו בסשן"""
        return getattr(self, 'session_seconds', 0)

    # ── Tick ─────────────────────────────────────────────────────

    def _on_tick(self):
        if not self._running or self._paused:
            return

        self.session_seconds += 1
        self.daily_used      += 1

        # חישוב זמן נותר
        remaining = self._get_remaining()

        # בדיקת פקיעת זמן
        if remaining is not None and remaining <= 0:
            self.stop()
            self.time_expired.emit()
            return

        # שליחת התראות
        if remaining is not None:
            self._check_warnings(remaining)

        # שליחת tick
        self.tick.emit(self.session_seconds, remaining)

        # מעקב אחרי אפליקציה נוכחית
        if self._current_app:
            self._tick_app(self._current_app)

        # שמירה כל שנייה בדיוק — לא כל 30 שניות
        # (שמירה ב-config כל שנייה יקרה מדי; במקום זאת שמור כל 10 שניות ושארית ב-stop/pause)
        if self.session_seconds % 10 == 0:
            delta = self.session_seconds - self._last_saved_at
            if delta > 0:
                self.cm.add_time_used(self.username, delta)
                self._last_saved_at = self.session_seconds

    def _get_remaining(self) -> int | None:
        """מחזיר שניות שנותרו, או None אם ללא הגבלה"""
        user = self.cm.get_user(self.username)
        if not user:
            return None

        daily_limit = user.get("time_limit_daily")
        if daily_limit is not None:
            used = self.cm.get_time_used_today(self.username) + self.session_seconds
            remaining = (daily_limit * 60) - used
            return max(0, remaining)

        total_limit = user.get("time_limit_total")
        if total_limit is not None:
            remaining = (total_limit * 60) - self.session_seconds
            return max(0, remaining)

        return None

    def _check_warnings(self, remaining_seconds: int):
        intervals = self.cm.get_warning_intervals()   # רשימת דקות
        for mins in intervals:
            secs = mins * 60
            # חלון ±3 שניות
            if abs(remaining_seconds - secs) <= 3 and secs not in self._warned_at:
                self._warned_at.add(secs)
                self.warning_signal.emit(remaining_seconds)

    # ── אפליקציות ─────────────────────────────────────────────────

    def set_current_app(self, app_name: str | None):
        """מגדיר את האפליקציה הפעילה כרגע לצורך ספירת זמן"""
        self._current_app = app_name

    def _tick_app(self, app_name: str):
        self._app_seconds[app_name] = self._app_seconds.get(app_name, 0) + 1
        used = self._app_seconds[app_name]

        user = self.cm.get_user(self.username)
        if not user:
            return

        app_limits = user.get("app_limits", {})
        limit_mins = None
        for key, val in app_limits.items():
            if key.lower() in app_name.lower():
                limit_mins = val
                break

        if limit_mins is not None:
            remaining = (limit_mins * 60) - used
            self.app_tick.emit(app_name, used, max(0, remaining))
            if remaining <= 0:
                self.app_expired.emit(app_name)
        else:
            self.app_tick.emit(app_name, used, None)

    def get_app_seconds(self, app_name: str) -> int:
        return self._app_seconds.get(app_name, 0)

    # ── שאילתות ───────────────────────────────────────────────────

    def get_session_seconds(self) -> int:
        return self.session_seconds

    def get_remaining_seconds(self) -> int | None:
        return self._get_remaining()

    @staticmethod
    def format_time(seconds: int) -> str:
        """פורמט שניות → hh:mm:ss"""
        if seconds < 0:
            seconds = 0
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def format_time_human(seconds: int) -> str:
        """פורמט שניות → 'X שעות Y דקות'"""
        if seconds < 0:
            seconds = 0
        h = seconds // 3600
        m = (seconds % 3600) // 60
        if h > 0 and m > 0:
            return f"{h} שעות {m} דקות"
        elif h > 0:
            return f"{h} שעות"
        elif m > 0:
            return f"{m} דקות"
        else:
            return f"{seconds} שניות"


    # ── elapsed ──────────────────────────────────────────────────
