"""
exit_screen.py - מסך יציאה (לאחר שימוש במחשב)
שומר הפתח v0.0.9
"""
import subprocess, ctypes
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QApplication,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from styles import get_exit_screen_style
from time_manager import TimeManager


def close_user_apps():
    """
    סוגר תוכנות משתמש בלבד — דפדפנים, עורכי טקסט, וכו'.
    ⚠️  לעולם לא יוצא מ-Windows.
    ⚠️  לעולם לא סוגר תהליכי Shell/Session של Windows.

    גישת whitelist: סוגר רק תוכנות 'בטוחות' שברור שהן אפליקציות משתמש.
    """
    # תוכנות שבטוח לסגור — דפדפנים, Office, קריאה, כלי עבודה נפוצים
    SAFE_TO_CLOSE_KEYWORDS = (
        "chrome", "firefox", "msedge", "brave", "opera", "vivaldi", "iexplore",
        "winword", "excel", "powerpnt", "outlook", "onenote", "publisher",
        "notepad", "wordpad", "write", "mspaint",
        "vlc", "wmplayer", "potplayer", "mpc-hc",
        "acrobat", "acrord32", "foxitreader", "sumatrapdf",
        "winrar", "7zfm", "peazip",
        "calc", "mscalc",
    )
    # תהליכי מערכת/shell שאסור לגעת בהם — גם אם נראים כ"משתמש"
    NEVER_CLOSE = {
        "explorer.exe", "svchost.exe", "system", "registry", "smss.exe",
        "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "dwm.exe",
        "fontdrvhost.exe", "winlogon.exe", "audiodg.exe", "spoolsv.exe",
        "cmd.exe", "conhost.exe", "taskhostw.exe", "sihost.exe",
        "runtimebroker.exe", "shellexperiencehost.exe",
        "searchui.exe", "searchapp.exe", "startmenuexperiencehost.exe",
        "applicationframehost.exe", "systemsettings.exe", "textinputhost.exe",
        "securityhealthservice.exe", "msmpeng.exe",
        "userinit.exe", "logonui.exe", "taskmgr.exe", "ctfmon.exe",
        "dllhost.exe", "werfault.exe", "wuauclt.exe",
        "ntoskrnl.exe", "lsm.exe", "wlanext.exe", "uhssvc.exe",
    }
    SHOMER_KEYWORDS = ("shomer", "שומר", "guardian", "hapetach")

    try:
        import psutil, os, sys

        shomer_pids: set = set()
        current = psutil.Process()
        shomer_pids.add(current.pid)
        try:
            p = current
            while True:
                p = p.parent()
                if p is None or p.pid <= 4: break
                shomer_pids.add(p.pid)
        except Exception:
            pass

        current_exe_dir = os.path.dirname(sys.executable).lower()

        for proc in psutil.process_iter(["pid", "name", "username", "exe", "cmdline"]):
            try:
                name    = (proc.info.get("name") or "").lower()
                pid     = proc.info.get("pid", 0)
                exe_p   = (proc.info.get("exe") or "").lower()
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()

                if pid <= 4: continue
                if pid in shomer_pids: continue
                if name in NEVER_CLOSE: continue
                if any(kw in name    for kw in SHOMER_KEYWORDS): continue
                if any(kw in exe_p   for kw in SHOMER_KEYWORDS): continue
                if any(kw in cmdline for kw in SHOMER_KEYWORDS): continue
                if name in ("python.exe", "pythonw.exe", "python3.exe"):
                    if os.path.dirname(exe_p) == current_exe_dir: continue

                uname = (proc.info.get("username") or "").upper()
                if any(s in uname for s in ("SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE")): continue

                # סגור רק תוכנות שמופיעות ב-SAFE_TO_CLOSE_KEYWORDS
                base = os.path.splitext(name)[0]
                if any(kw in base for kw in SAFE_TO_CLOSE_KEYWORDS):
                    try:
                        proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception:
                pass
    except ImportError:
        pass


def clean_temp_files():
    """מנקה קבצים זמניים"""
    import os, shutil, tempfile
    temp = tempfile.gettempdir()
    for item in os.listdir(temp):
        try:
            fp = os.path.join(temp, item)
            if os.path.isfile(fp): os.unlink(fp)
            elif os.path.isdir(fp): shutil.rmtree(fp, ignore_errors=True)
        except: pass



def detect_usb_drives(excluded: list = None) -> list:
    """מחזיר רשימת כונני USB מחוברים (אותיות)"""
    excluded = [x.upper() for x in (excluded or [])]
    drives = []
    try:
        import string, ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        DRIVE_REMOVABLE = 2
        for i, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                drive = f"{letter}:\\"
                if letter.upper() in excluded:
                    continue
                dtype = ctypes.windll.kernel32.GetDriveTypeW(drive)
                if dtype == DRIVE_REMOVABLE:
                    drives.append(letter)
    except Exception:
        pass
    return drives

class ExitScreen(QWidget):
    """
    מסך יציאה מלא-מסך שמוצג 5 שניות אחרי לחיצה על יציאה.
    מציג: זמן שימוש אחרון + זמן נותר + הודעות מותאמות אישית.
    """
    exit_done = pyqtSignal()   # כשהסיים → חזור למסך נעילה

    def __init__(self, config_manager, username: str,
                 session_seconds: int, remaining: int | None,
                 dark: bool = False, parent=None):
        super().__init__(parent)
        self.cm              = config_manager
        self.username        = username
        self.session_seconds = session_seconds
        self.remaining       = remaining
        self.dark            = dark

        cfg = config_manager.get_exit_screen_cfg()
        self._duration = cfg.get("duration_seconds", 5)
        self._countdown = self._duration
        self._custom_msgs = cfg.get("custom_messages", [])

        self._setup_window()
        self._build_ui()
        self.setStyleSheet(get_exit_screen_style(dark))
        self._start()

        # ביצוע פעולות ניקוי
        if cfg.get("close_user_apps", True):
            QTimer.singleShot(200, close_user_apps)
        if cfg.get("clean_temp", False):
            QTimer.singleShot(500, clean_temp_files)

    def _setup_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setObjectName("ExitScreen")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.showFullScreen()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addStretch()

        center = QHBoxLayout(); center.addStretch()

        card = QFrame(); card.setObjectName("ExitCard"); card.setFixedWidth(480)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(60); sh.setColor(QColor(0,0,0,80)); sh.setOffset(0,12)
        card.setGraphicsEffect(sh)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(44,40,44,40); cl.setSpacing(16)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # אייקון + ברכת פרידה
        icon = QLabel("👋"); icon.setStyleSheet("font-size:52px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter); cl.addWidget(icon)

        user = self.cm.get_user(self.username) or {}
        name = user.get("display_name") or self.username
        ttl = QLabel(f"להתראות, {name}!")
        ttl.setObjectName("ExitTitle")
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(ttl)

        cl.addSpacing(8)

        # זמן שימוש
        dur_lbl = QLabel(f"משך הסשן: {TimeManager.format_time_human(self.session_seconds)}")
        dur_lbl.setObjectName("ExitSub")
        dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dur_lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(dur_lbl)

        # זמן נותר
        if self.remaining is not None:
            rem_str = TimeManager.format_time_human(self.remaining)
            rem_color = "#22c55e" if self.remaining > 600 else "#f59e0b" if self.remaining > 120 else "#ef4444"
            rem_lbl = QLabel(f"נותר היום: {rem_str}")
            rem_lbl.setStyleSheet(f"color:{rem_color}; font-size:20px; font-weight:600;"
                                   "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
            rem_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rem_lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            cl.addWidget(rem_lbl)
        else:
            # הצג שעון שימוש
            total_secs = self.cm.get_time_used_today(self.username)
            tot_lbl = QLabel(f"שימוש היום: {TimeManager.format_time_human(total_secs)}")
            tot_lbl.setObjectName("ExitSub")
            tot_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); cl.addWidget(tot_lbl)

        # הודעות מותאמות
        for msg_cfg in self._custom_msgs:
            text = msg_cfg.get("text","")
            if text:
                style = msg_cfg.get("style","")
                m_lbl = QLabel(text); m_lbl.setObjectName("ExitMsg")
                if style: m_lbl.setStyleSheet(style)
                m_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                m_lbl.setWordWrap(True)
                m_lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                cl.addWidget(m_lbl)

        cl.addSpacing(16)

        # אזהרת USB
        cfg_exit = self.cm.get_exit_screen_cfg()
        if cfg_exit.get("detect_usb", True):
            excluded = cfg_exit.get("excluded_drives", [])
            usbs = detect_usb_drives(excluded)
            if usbs:
                usb_lbl = QLabel(f"⚠️  לא לשכוח לקחת את האון-קי! ({', '.join(usbs + [':'])})")
                usb_lbl.setStyleSheet("color:#f59e0b; font-size:15px; font-weight:700;"
                    "background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3);"
                    "border-radius:8px; padding:8px 14px;"
                    "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
                usb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                usb_lbl.setWordWrap(True)
                cl.addWidget(usb_lbl)

        # ספירה לאחור
        self._count_lbl = QLabel(f"חוזר למסך הנעילה בעוד {self._countdown}...")
        self._count_lbl.setObjectName("ExitSub")
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); cl.addWidget(self._count_lbl)

        # Progress bar
        self._prog = QFrame()
        self._prog.setFixedHeight(4)
        self._prog.setStyleSheet(f"background:{'#388bfd' if self.dark else '#2563eb'}; border-radius:2px;")
        self._prog_max = 392
        self._prog.setFixedWidth(self._prog_max)
        cl.addWidget(self._prog, 0, Qt.AlignmentFlag.AlignCenter)

        center.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
        center.addStretch()
        root.addLayout(center)
        root.addStretch()

    def _start(self):
        self._elapsed_ms = 0
        total_ms = self._duration * 1000

        self._timer = QTimer()
        self._timer.setInterval(100)
        self._timer.timeout.connect(lambda: self._tick(total_ms))
        self._timer.start()

    def _tick(self, total_ms):
        self._elapsed_ms += 100
        ratio = max(0, 1 - self._elapsed_ms / total_ms)
        self._prog.setFixedWidth(int(self._prog_max * ratio))

        remaining_secs = max(0, (total_ms - self._elapsed_ms) // 1000)
        self._count_lbl.setText(f"חוזר למסך הנעילה בעוד {remaining_secs}...")

        if self._elapsed_ms >= total_ms:
            self._timer.stop()
            self.exit_done.emit()

    def closeEvent(self, event):
        # מאפשר סגירה רגילה (נקרא על ידי main.py לאחר exit_done)
        if self._timer:
            self._timer.stop()
        event.accept()

    def shutdown(self):
        """סגירה מבוקרת מ-main.py"""
        if hasattr(self, '_timer') and self._timer:
            self._timer.stop()
        self.close()
