"""
screen_off_manager.py - ניהול כיבוי תאורת המסך לפי תרחישים
שומר הפתח v2.0

כיבוי/הדלקת צג בלבד — המחשב ממשיך לפעול.
"""
import ctypes
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── קבועי Windows ──────────────────────────────────────────────────
SC_MONITORPOWER = 0xF170
HWND_BROADCAST  = ctypes.wintypes.HWND(0xFFFF)
WM_SYSCOMMAND   = 0x0112
MONITOR_OFF     = 2
MONITOR_ON      = -1


def _turn_monitor_off():
    """כיבוי תאורת צג (ב-Windows)"""
    try:
        ctypes.windll.user32.SendMessageW(
            HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF
        )
        logger.info("מסך כובה")
    except Exception as e:
        logger.warning(f"כיבוי מסך נכשל: {e}")


def _turn_monitor_on():
    """
    הדלקת תאורת צג — Windows דורש סימולציה של פעילות
    (mouse move ריק / keybd_event לא מפריעה לפוקוס).
    """
    try:
        ctypes.windll.user32.SendMessageW(
            HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_ON
        )
        # הזזת עכבר של 1px ובחזרה — מעירה את הצג אמינה יותר
        ctypes.windll.user32.mouse_event(0x0001, 1, 0, 0, 0)  # MOUSEEVENTF_MOVE
        ctypes.windll.user32.mouse_event(0x0001, -1, 0, 0, 0)
        logger.info("מסך הודלק")
    except Exception as e:
        logger.warning(f"הדלקת מסך נכשלה: {e}")


def _get_last_input_seconds() -> float:
    """מחזיר שניות מאז פעילות המשתמש האחרונה"""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        elapsed_ms = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return elapsed_ms / 1000.0
    except Exception:
        return 0.0


class ScreenOffOverlay:
    """
    חלון קטן שמוצג על המסך בזמן שהצג אמור להיות כבוי
    (לאחר שחידוש פעילות הדליק אותו מחדש).
    מציג הודעה + טיימר לאחור.
    """

    def __init__(self, delay_secs: int):
        self._delay = delay_secs
        self._widget = None
        self._timer  = None

    def show(self, callback_turn_off):
        """מציג את ההתראה ב-thread של Qt"""
        try:
            from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
            from PyQt6.QtCore    import Qt, QTimer
            from PyQt6.QtGui     import QColor

            self._remaining = self._delay

            w = QWidget(None, Qt.WindowType.FramelessWindowHint |
                              Qt.WindowType.WindowStaysOnTopHint |
                              Qt.WindowType.Tool)
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

            layout = QVBoxLayout(w)
            layout.setContentsMargins(20, 14, 20, 14)

            lbl = QLabel()
            lbl.setStyleSheet(
                "QLabel{"
                "background:rgba(0,0,0,0.78);color:white;"
                "border-radius:12px;padding:14px 22px;"
                "font-size:15px;font-weight:600;"
                "font-family:'Segoe UI','Arial Hebrew',sans-serif;"
                "}"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

            def _update():
                lbl.setText(
                    f"מסך המחשב מוגדר כעת להיות כבוי\n"
                    f"יכבה בעוד כ- {self._remaining} שניות"
                )
                lbl.adjustSize(); w.adjustSize()
                # מיקום מרכז-עליון
                try:
                    screen = QApplication.primaryScreen().geometry()
                    w.move((screen.width() - w.width()) // 2, 60)
                except Exception:
                    pass

                self._remaining -= 1
                if self._remaining < 0:
                    self._timer.stop()
                    w.close()
                    self._widget = None
                    callback_turn_off()

            self._widget = w
            _update()
            w.show()

            self._timer = QTimer()
            self._timer.setInterval(1000)
            self._timer.timeout.connect(_update)
            self._timer.start()

        except Exception as e:
            logger.warning(f"ScreenOffOverlay נכשל: {e}")
            # fallback — כבה ישירות
            callback_turn_off()

    def hide(self):
        """מסתיר את ההתראה (כשהמשתמש פעיל מחדש)"""
        if self._timer:
            try: self._timer.stop()
            except: pass
        if self._widget:
            try: self._widget.close()
            except: pass
            self._widget = None
        self._timer   = None


class ScreenOffManager:
    """
    מנוע הכיבוי שרץ ב-thread רקע.
    - בודק כל 30 שניות אם הזמן הנוכחי בתוך תרחיש כיבוי.
    - אם כן → מכבה מסך.
    - אם המשתמש מדליק מחדש (ומוגדר re-off) → מציג overlay + מכבה שוב.
    """

    CHECK_INTERVAL = 30   # שניות בין בדיקות תרחיש

    def __init__(self, config_manager):
        self.cm         = config_manager
        self._running   = False
        self._thread    = None
        self._off_now   = False   # True כשאנו בתוך תרחיש כיבוי
        self._overlay   = None
        self._reoff_watcher_active = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="ScreenOffMgr", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False

    # ── לולאה ראשית ────────────────────────────────────────────────

    def _loop(self):
        last_check = 0
        while self._running:
            now_ts = time.time()

            if now_ts - last_check >= self.CHECK_INTERVAL:
                last_check = now_ts
                should_off = self._should_be_off()

                if should_off and not self._off_now:
                    # כנסנו לחלון כיבוי
                    self._off_now = True
                    _turn_monitor_off()
                    self._start_reoff_watcher()

                elif not should_off and self._off_now:
                    # יצאנו מחלון הכיבוי — הדלק
                    self._off_now = False
                    self._stop_reoff_watcher()
                    _turn_monitor_on()

            time.sleep(5)

    # ── בדיקת תרחיש ────────────────────────────────────────────────

    def _should_be_off(self) -> bool:
        cfg = self.cm.config.get("screen_off", {})
        now = datetime.now()

        # כיבוי בחסימה
        if cfg.get("off_when_blocked", False):
            for block in self.cm.config.get("global_blocks", []):
                if self.cm._matches_block(block, now):
                    return True

        # תרחישים
        for s in cfg.get("scenarios", []):
            if self._matches_scenario(s, now):
                return True

        return False

    def _matches_scenario(self, s: dict, now: datetime) -> bool:
        stype     = s.get("type", "weekday")
        time_from = s.get("time_from", "")
        time_to   = s.get("time_to",   "")

        def _time_in_range():
            if not time_from or not time_to:
                return True
            cur = now.strftime("%H:%M")
            if time_from <= time_to:
                return time_from <= cur <= time_to
            return cur >= time_from or cur <= time_to

        if stype == "weekday":
            py_to_il = {6:0,0:1,1:2,2:3,3:4,4:5,5:6}
            il_day = py_to_il.get(now.weekday(), now.weekday())
            return il_day in s.get("days", []) and _time_in_range()

        if stype == "daterange":
            ds = now.strftime("%Y-%m-%d")
            df = s.get("date_from",""); dt_ = s.get("date_to","")
            if df and dt_ and not (df <= ds <= dt_):
                return False
            return _time_in_range()

        return False

    # ── re-off watcher ──────────────────────────────────────────────

    def _start_reoff_watcher(self):
        """עוקב אחרי פעילות משתמש — כשמדליק מחדש, מציג overlay וכובה שוב"""
        cfg = self.cm.config.get("screen_off", {})
        if not cfg.get("reoff_enabled", False):
            return
        if self._reoff_watcher_active:
            return
        self._reoff_watcher_active = True
        delay = cfg.get("reoff_delay_secs", 30)
        threading.Thread(
            target=self._reoff_loop, args=(delay,), daemon=True
        ).start()

    def _stop_reoff_watcher(self):
        self._reoff_watcher_active = False
        if self._overlay:
            try:
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self._overlay._widget,
                    "close",
                    Qt.ConnectionType.QueuedConnection
                )
            except Exception:
                pass
            self._overlay = None

    def _reoff_loop(self, delay: int):
        """
        בזמן שהמסך אמור להיות כבוי:
        כשמזהה פעילות → מראה overlay עם ספירה לאחור → כובה שוב.
        """
        # המתן מעט לפני שמתחיל לעקוב
        time.sleep(3)
        was_active = False

        while self._reoff_watcher_active and self._running:
            idle = _get_last_input_seconds()
            is_active = idle < 2.0   # משתמש פעיל בשתי שניות האחרונות

            if is_active and not was_active:
                # פעילות חדשה — הצג overlay
                try:
                    from PyQt6.QtCore import QMetaObject, Qt
                    from PyQt6.QtWidgets import QApplication
                    self._overlay = ScreenOffOverlay(delay)
                    # הצג בthread של Qt
                    QMetaObject.invokeMethod(
                        QApplication.instance(),
                        "processEvents",
                        Qt.ConnectionType.QueuedConnection
                    )
                    threading.Thread(
                        target=lambda: self._overlay.show(self._do_reoff),
                        daemon=True
                    ).start()
                except Exception as e:
                    logger.warning(f"reoff overlay: {e}")

            elif not is_active and was_active:
                # עצר פעילות — הסתר overlay ואפס
                if self._overlay:
                    self._overlay.hide()
                    self._overlay = None

            was_active = is_active
            time.sleep(1)

    def _do_reoff(self):
        """כיבוי מחדש לאחר הספירה"""
        if self._reoff_watcher_active and self._off_now:
            _turn_monitor_off()
            self._overlay = None
