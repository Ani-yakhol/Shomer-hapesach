"""
main.py - נקודת כניסה ראשית
שומר הפתח v2.0
"""

import sys
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# ── לוג ────────────────────────────────────────────────────────────
import logging

def _setup_logging():
    log_dir = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "ShomerHaPetach"
    )
    try:
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(log_dir, "shomer.log"),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            encoding="utf-8",
        )
    except Exception:
        logging.basicConfig(level=logging.INFO)

_setup_logging()
logger = logging.getLogger(__name__)

# ── PyQt6 ──────────────────────────────────────────────────────────
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont
except ImportError:
    try:
        import tkinter as tk, tkinter.messagebox as mb
        root = tk.Tk(); root.withdraw()
        mb.showerror("שומר הפתח", "PyQt6 לא מותקן!\nהרץ:  pip install PyQt6 pywin32 psutil")
    except Exception:
        pass
    sys.exit(1)

from datetime import datetime
from config_manager import ConfigManager
from lock_screen    import LockScreen, set_taskbar_visible
from welcome_screen import WelcomeScreen
from exit_screen    import ExitScreen
from admin_panel    import AdminPanel
from time_manager   import TimeManager
from session_widget import SessionWidget
from kiosk_screen    import KioskScreen
from keyboard_hook   import KeyboardBlocker
from screen_off_manager import ScreenOffManager
from print_monitor   import PrintMonitor


class ShomerHaPetach:
    def __init__(self, app: QApplication):
        self.app = app
        self.cm  = ConfigManager()

        self._lock_screen    : LockScreen    | None = None
        self._welcome_screen : WelcomeScreen | None = None
        self._exit_screen    : ExitScreen    | None = None
        self._admin_panel    : AdminPanel    | None = None
        self._session_widget : SessionWidget | None = None
        self._time_manager   : TimeManager   | None = None
        self._notif                                 = None

        self._current_user    : str | None = None
        self._session_start   : datetime | None = None
        self._from_lock_admin : bool = False

        self._kb_hook: KeyboardBlocker | None = None
        self._screen_off_mgr = ScreenOffManager(self.cm)
        self._screen_off_mgr.start()

        # ניטור מדפסות ברקע
        self._print_monitor = PrintMonitor(
            self.cm,
            get_current_user_fn=lambda: self._current_user,
            on_print_charged_fn=self._on_print_charged,
        )
        self._print_monitor.start()

        QTimer.singleShot(600, self._apply_startup_settings)
        self._show_lock_screen()

    # ── הגדרות הפעלה ─────────────────────────────────────────────
    def _start_kb_hook(self):
        """
        מפעיל / מחדש את חסימת מקשי המערכת.
        אם ה-hook קיים ורק מושהה — מחדש אותו (מהיר יותר ואמין יותר).
        אם לא קיים — יוצר חדש.
        """
        try:
            ls = self.cm.get_lock_screen_cfg()
            hotkey = ls.get("admin_hotkey", "F8")
            if self._kb_hook and self._kb_hook._thread and self._kb_hook._thread.is_alive():
                # ה-hook קיים — פשוט הפעל מחדש (resume)
                self._kb_hook._active = True
                logger.info("Keyboard hook חודש (resume)")
            else:
                # צור hook חדש
                if self._kb_hook:
                    try: self._kb_hook.stop()
                    except Exception: pass
                self._kb_hook = KeyboardBlocker(
                    admin_hotkey_callback=self._on_kb_admin_hotkey,
                    admin_hotkey=hotkey,
                )
                self._kb_hook.start()
                logger.info("Keyboard hook הופעל (חדש)")
        except Exception as e:
            logger.warning(f"keyboard hook: {e}")

    def _on_kb_admin_hotkey(self):
        """נקרא מ-keyboard hook ב-thread נפרד"""
        if self._lock_screen:
            self._lock_screen.on_admin_hotkey()

    def _stop_kb_hook(self):
        """
        בזמן סשן משתמש — מפסיק זמנית את החסימה (pause) ללא הריסת ה-hook.
        ה-hook יחודש בקריאה הבאה ל-_start_kb_hook.
        """
        try:
            if self._kb_hook:
                self._kb_hook._active = False   # pause — לא stop מלא
        except Exception as e:
            logger.warning(f"stop hook: {e}")

    def _apply_startup_settings(self):
        try:
            from registry_manager import (
                block_ctrl_alt_del, unblock_ctrl_alt_del, add_to_startup
            )
            cfg = self.cm.get_general_cfg()
            if cfg.get("block_ctrl_alt_del", True):
                block_ctrl_alt_del()
            else:
                unblock_ctrl_alt_del()
            if cfg.get("startup_enabled", True):
                add_to_startup()
        except Exception as e:
            logger.warning(f"הגדרות הפעלה (לא קריטי): {e}")

    # ══════════════════════════════════════════════════════════════
    # מסך נעילה
    # ══════════════════════════════════════════════════════════════
    def _show_lock_screen(self, remaining_text: str = ""):
        self._close_screens()
        set_taskbar_visible(False)
        # הפעל מחדש NoWinKeys וחסימת Ctrl+Alt+Del בכל הצגת מסך נעילה
        QTimer.singleShot(200, self._apply_security_settings)

        dark = self.cm.is_dark_mode()
        self._lock_screen = LockScreen(
            self.cm, dark=dark, show_remaining=remaining_text
        )
        self._lock_screen.login_success.connect(self._on_login)
        self._lock_screen.admin_requested.connect(self._on_admin_from_lock)
        self._lock_screen.show()
        self._lock_screen.activateWindow()
        self._lock_screen.raise_()
        QTimer.singleShot(400, self._start_kb_hook)
        logger.info("מסך נעילה מוצג")

    def _apply_security_settings(self):
        """מחיל הגדרות אבטחה — נקרא בכל הצגת מסך נעילה"""
        try:
            from registry_manager import block_ctrl_alt_del
            block_ctrl_alt_del()
        except Exception as e:
            logger.warning(f"הגדרות אבטחה: {e}")

    def _on_login(self, username: str):
        """משתמש הזין סיסמה נכונה → מסך כניסה"""
        logger.info(f"כניסה: {username}")
        self._current_user  = username
        self._session_start = datetime.now()

        set_taskbar_visible(True)
        self._stop_kb_hook()

        if self._lock_screen:
            self._lock_screen.hide()

        self._show_welcome(username)

    def _on_admin_from_lock(self):
        """F8 → פאנל הגדרות ישיר"""
        logger.info("כניסת מנהל מ-F8")
        admins = self.cm.get_admin_users()
        self._current_user    = admins[0] if admins else "מנהל מערכת"
        self._session_start   = datetime.now()
        self._from_lock_admin = True

        set_taskbar_visible(True)
        self._stop_kb_hook()

        if self._lock_screen:
            self._lock_screen.hide()

        QTimer.singleShot(150, self._open_admin)

    # ══════════════════════════════════════════════════════════════
    # מסך כניסה (Welcome)
    # ══════════════════════════════════════════════════════════════
    def _show_welcome(self, username: str, is_returning: bool = False):
        dark = self.cm.is_dark_mode()
        try:
            self._welcome_screen = WelcomeScreen(
                self.cm, username, dark=dark, is_returning=is_returning
            )
            self._welcome_screen.enter_requested.connect(self._on_enter)
            self._welcome_screen.settings_requested.connect(self._on_settings)
            self._welcome_screen.exit_requested.connect(self._on_exit_from_welcome)
            self._welcome_screen.show()
            self._welcome_screen.activateWindow()
            self._welcome_screen.raise_()
        except Exception as _e:
            import traceback
            logger.error(f"מסך כניסה קרס: {traceback.format_exc()}")
            QMessageBox.critical(None, "שגיאה", f"מסך כניסה קרס:\n{_e}\n\nראה shomer.log לפרטים")
            self._show_lock_screen()

    def _on_enter(self):
        username = self._current_user
        if self._welcome_screen:
            self._welcome_screen.hide()
            self._welcome_screen = None

        # אם יש TimeManager מושהה (חזרה מ-Welcome) — המשך ספירה מאיפה שעצר
        if self._time_manager and self._time_manager._paused:
            self._time_manager.resume()
            if self._session_widget:
                self._session_widget.show()
            return

        user = self.cm.get_user(username) or {}
        kiosk = self.cm.config.get("kiosk", {})
        if kiosk.get("enabled") and not user.get("is_admin"):
            self._start_kiosk(username)
        else:
            self._start_session(username)

    def _start_kiosk(self, username: str):
        dark = self.cm.is_dark_mode()
        self._kiosk_screen = KioskScreen(self.cm, username, dark=dark)
        self._kiosk_screen.logout_requested.connect(lambda: self._on_kiosk_logout(username))
        self._kiosk_screen.show()
        self._kiosk_screen.activateWindow()

    def _on_kiosk_logout(self, username: str):
        if hasattr(self,"_kiosk_screen") and self._kiosk_screen:
            self._kiosk_screen.close()
            self._kiosk_screen = None
        self._current_user  = None
        self._session_start = None
        self._show_lock_screen()

    def _on_settings(self):
        if self._welcome_screen:
            self._welcome_screen.hide()
        self._from_lock_admin = False
        QTimer.singleShot(150, self._open_admin)

    def _on_exit_from_welcome(self):
        """לחיצה על יציאה ממסך כניסה"""
        if self._welcome_screen:
            self._welcome_screen.close()
            self._welcome_screen = None

        # אם זה לאחר שימוש (TimeManager קיים ומושהה) — עשה יציאה מלאה עם מסך יציאה
        if self._time_manager:
            self._on_logout()
            return

        self._current_user  = None
        self._session_start = None
        self._show_lock_screen()

    # ══════════════════════════════════════════════════════════════
    # סשן שימוש
    # ══════════════════════════════════════════════════════════════
    def _start_session(self, username: str):
        dark = self.cm.is_dark_mode()

        set_taskbar_visible(True)

        # ווידג'ט זמן צף
        try:
            self._session_widget = SessionWidget(self.cm, username, dark=dark)
            self._session_widget.logout_requested.connect(self._on_logout)
            self._session_widget.welcome_requested.connect(self._on_welcome_from_session)
            self._session_widget.show()
        except Exception as e:
            logger.error(f"SessionWidget נכשל: {e}")

        # מנהל זמן
        try:
            self._time_manager = TimeManager(self.cm, username)
            self._time_manager.tick.connect(self._on_tick)
            self._time_manager.warning_signal.connect(self._on_warning)
            self._time_manager.time_expired.connect(lambda: self._on_logout(force=True))
            self._time_manager.start()
        except Exception as e:
            logger.error(f"TimeManager נכשל: {e}")

        # היסטוריה
        try:
            self.cm.add_session_history(username, {
                "date":             datetime.now().strftime("%Y-%m-%d"),
                "login_time":       datetime.now().strftime("%H:%M"),
                "duration_seconds": 0,
                "prints":           0,
            })
        except Exception as e:
            logger.warning(f"שמירת היסטוריה נכשלה: {e}")

    def _on_tick(self, elapsed, remaining):
        if self._session_widget:
            try:
                self._session_widget.update_time(elapsed, remaining)
            except Exception:
                pass

    def _on_warning(self, seconds_left: int):
        try:
            from notification_widget import NotificationWidget
            dark = self.cm.is_dark_mode()
            mins = seconds_left // 60
            msg  = f"⚠️  נותרו {mins} דקות לשימוש" if mins > 0 else "⚠️  פחות מדקה נותרה!"
            if self._notif:
                try: self._notif.close()
                except: pass
            self._notif = NotificationWidget(msg, seconds_left, dark=dark)
            self._notif.show()
        except Exception as e:
            logger.warning(f"התראה נכשלה: {e}")

    def _on_print_charged(self, msg: str, pages: int, type_label: str, cost: float):
        """Toast notification לאחר הדפסה — נקרא מ-PrintMonitor ב-thread רקע"""
        QTimer.singleShot(0, lambda: self._show_print_toast(msg, cost))

    def _show_print_toast(self, msg: str, cost: float):
        """מציג Toast הודעת הדפסה ב-thread של Qt"""
        try:
            from notification_widget import NotificationWidget
            dark = self.cm.is_dark_mode()
            # שמור reference — ללא זה Qt מוחק את החלונית מיד (GC)
            self._print_notif = NotificationWidget(f"🖨  {msg}", 0, dark=dark)
            if cost > 0:
                self._print_notif._rem_lbl.setText(f"עלות: ₪{cost:.2f}")
            else:
                self._print_notif._rem_lbl.setText("")
            self._print_notif.show()
        except Exception as e:
            logger.warning(f"print toast נכשל: {e}")

    def _on_welcome_from_session(self):
        """לחיצה על 📋 בווידג'ט → מסך כניסה עם 'המשך שימוש', עצירת ספירה מדויקת"""
        username = self._current_user
        if not username:
            return
        # עצור ספירה — pause() שומר את השארית לקובץ
        if self._time_manager:
            self._time_manager.pause()
        # הסתר ווידג'ט (אל תסגור — ימשיך לאחר חזרה)
        if self._session_widget:
            self._session_widget.hide()
        self._show_welcome(username, is_returning=True)

    def _on_logout(self, force: bool = False):
        """
        יציאת משתמש מהתוכנה — חוזר למסך הנעילה.
        ⚠️  פעולה זו לעולם לא יוצאת מ-Windows, רק מחשבון המשתמש בשומר הפתח.
        """
        username = self._current_user

        # ── סגור את כל המסכים הפתוחים של המשתמש ──
        if self._welcome_screen:
            try: self._welcome_screen.close()
            except: pass
            self._welcome_screen = None

        elapsed = 0
        if self._time_manager:
            elapsed = self._time_manager.elapsed_seconds()
            self._time_manager.stop()
            self._time_manager = None

        # עדכן היסטוריה
        try:
            user = self.cm.get_user(username)
            if user and user.get("session_history"):
                user["session_history"][-1]["duration_seconds"] = elapsed
                self.cm.save()
        except Exception:
            pass

        if self._session_widget:
            try: self._session_widget.close()
            except: pass
            self._session_widget = None

        remaining = self.cm.get_remaining_time_today(username) if username else None
        cfg = self.cm.get_exit_screen_cfg()

        if cfg.get("enabled", True):
            self._show_exit(username, elapsed, remaining)
        else:
            self._current_user  = None
            self._session_start = None
            rem = TimeManager.format_time_human(remaining) if remaining else ""
            self._show_lock_screen(f"נותר היום: {rem}" if rem else "")

    def _show_exit(self, username, elapsed, remaining):
        dark = self.cm.is_dark_mode()
        self._exit_screen = ExitScreen(
            self.cm, username, elapsed, remaining, dark=dark
        )
        self._exit_screen.exit_done.connect(self._on_exit_done)
        self._exit_screen.show()

    def _on_exit_done(self):
        username  = self._current_user
        remaining = self.cm.get_remaining_time_today(username) if username else None

        # ניקוי exit screen
        if self._exit_screen:
            try: self._exit_screen.shutdown()
            except: pass
            try: self._exit_screen.close()
            except: pass
            self._exit_screen = None

        # ניקוי כל שאריות של המשתמש הקודם
        for attr in ("_welcome_screen", "_session_widget"):
            w = getattr(self, attr, None)
            if w:
                try: w.close()
                except: pass
                setattr(self, attr, None)

        # אפס משתמש לפני מסך נעילה
        self._current_user  = None
        self._session_start = None
        self._time_manager  = None

        rem = TimeManager.format_time_human(remaining) if remaining else ""
        self._show_lock_screen(f"נותר היום: {rem}" if rem else "")

    # ══════════════════════════════════════════════════════════════
    # פאנל הגדרות
    # ══════════════════════════════════════════════════════════════
    def _open_admin(self):
        dark = self.cm.is_dark_mode()

        if self._welcome_screen:
            self._welcome_screen.hide()
        if self._lock_screen:
            self._lock_screen.hide()

        try:
            self._admin_panel = AdminPanel(self.cm, dark=dark)
            self._admin_panel.panel_closed.connect(self._on_admin_closed)
            self._admin_panel.show()
            self._admin_panel.raise_()
            self._admin_panel.activateWindow()
            logger.info("פאנל הגדרות נפתח")
        except Exception as _admin_err:
            import traceback
            err_msg = traceback.format_exc()
            logger.error(f"פאנל הגדרות קרס: {err_msg}")
            QMessageBox.critical(None, "שגיאה בפאנל ההגדרות",
                f"פאנל ההגדרות נכשל לפתוח.\n\nשגיאה:\n{str(_admin_err)}\n\nפרטים מלאים ב-shomer.log")
            self._on_admin_closed()

    def _on_admin_closed(self):
        self._admin_panel = None
        logger.info("פאנל הגדרות נסגר")

        if self._from_lock_admin:
            self._from_lock_admin = False
            self._current_user    = None
            self._session_start   = None
            self._show_lock_screen()
        else:
            username = self._current_user
            if username:
                self._show_welcome(username)
            else:
                self._show_lock_screen()

    # ══════════════════════════════════════════════════════════════
    # ניקוי
    # ══════════════════════════════════════════════════════════════
    def _close_screens(self):
        for attr in ("_welcome_screen", "_exit_screen", "_session_widget"):
            w = getattr(self, attr, None)
            if w:
                try:
                    if hasattr(w, 'shutdown'):
                        w.shutdown()
                    else:
                        w.close()
                except: pass
                setattr(self, attr, None)


# ══════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("שומר הפתח")
    app.setApplicationVersion("0.0.10")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    try:
        app.setFont(QFont("Segoe UI", 10))
    except Exception:
        pass

    logger.info("=" * 40)
    logger.info("שומר הפתח v0.0.10 מופעל")

    guard = ShomerHaPetach(app)   # noqa — must stay in scope
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
