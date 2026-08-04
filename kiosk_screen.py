"""
kiosk_screen.py - מסך קיוסק
שומר הפתח v2.0

לא חל על מנהל מערכת.
"""
import os, subprocess, ctypes
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QApplication, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont
from styles import get_welcome_style
from time_manager import TimeManager


def _find_exe(exe_name: str) -> str:
    """
    מוצא את הנתיב המלא של קובץ EXE.
    מחפש ב-PATH ובתיקיות Program Files.
    """
    import shutil
    # ניסיון 1: shutil.which
    found = shutil.which(exe_name)
    if found: return found

    # ניסיון 2: תיקיות נפוצות
    search_dirs = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        os.environ.get("SystemRoot", "C:\\Windows"),
        os.path.join(os.environ.get("SystemRoot","C:\\Windows"), "System32"),
        os.environ.get("LocalAppData", ""),
    ]
    for d in search_dirs:
        if not d: continue
        for root, dirs, files in os.walk(d):
            if exe_name.lower() in [f.lower() for f in files]:
                return os.path.join(root, exe_name)
            # מניעת חיפוש עמוק מדי
            if root.count(os.sep) - d.count(os.sep) >= 3:
                dirs.clear()
    return exe_name  # fallback — שם בלבד


class KioskScreen(QWidget):
    """מסך קיוסק — מוצג במקום שולחן העבודה"""
    logout_requested = pyqtSignal()

    def __init__(self, config_manager, username: str, dark: bool = False, parent=None):
        super().__init__(parent)
        self.cm       = config_manager
        self.username = username
        self.dark     = dark

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.showFullScreen()
        self.setObjectName("WelcomeScreen")
        self.setStyleSheet(get_welcome_style(dark))

        self._build_ui()

        # עצור hook מקשים בזמן קיוסק (המשתמש צריך להקיש בתוכנות)
        # כפתור יציאה מוסתר — רק F8 עם סיסמת מנהל

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet(
            "background:#1e40af; border-bottom:2px solid rgba(255,255,255,0.15);"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(28,0,28,0)

        logo = QLabel("🏪  מצב קיוסק – שומר הפתח")
        logo.setStyleSheet("color:white;font-size:16px;font-weight:700;"
                           "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
        hl.addWidget(logo)
        hl.addStretch()

        # שעון
        self._clock = QLabel("")
        self._clock.setStyleSheet("color:rgba(255,255,255,0.85);font-size:22px;"
                                  "font-family:'Segoe UI',sans-serif;")
        hl.addWidget(self._clock)
        self._clock_timer = QTimer(); self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(); self._tick_clock()

        hl.addSpacing(24)

        logout_btn = QPushButton("יציאה ✕")
        logout_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.18);color:white;border:1px solid "
            "rgba(255,255,255,0.3);border-radius:8px;padding:6px 18px;font-size:13px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.3);}"
        )
        logout_btn.clicked.connect(self._on_logout)
        hl.addWidget(logout_btn)
        root.addWidget(hdr)

        # ── גוף ——
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(40, 30, 40, 30)
        cl.setSpacing(20)

        user = self.cm.get_user(self.username) or {}
        name = user.get("display_name") or self.username
        title = QLabel(f"שלום, {name}")
        title.setStyleSheet("font-size:24px;font-weight:700;color:#1e3a5f;"
                            "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
        title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cl.addWidget(title)

        kiosk = self.cm.config.get("kiosk", {})
        allowed = kiosk.get("allowed_apps", [])

        if not allowed:
            empty = QLabel("לא הוגדרו תוכנות מאושרות\nפנה למנהל המערכת")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("font-size:16px;color:#6b7280;")
            cl.addWidget(empty)
        else:
            grid = QGridLayout(); grid.setSpacing(20)
            for i, app_exe in enumerate(allowed):
                btn = self._make_app_btn(app_exe)
                grid.addWidget(btn, i // 5, i % 5)
            cl.addLayout(grid)

        cl.addStretch()
        scroll.setWidget(center)
        root.addWidget(scroll)

    def _make_app_btn(self, exe_name: str) -> QPushButton:
        # שם תצוגה
        base = os.path.splitext(os.path.basename(exe_name))[0]
        display = base.replace("_"," ").replace("-"," ").title()

        # נסה לקבל אייקון אמיתי
        btn = QPushButton(f"🖥\n{display}")
        btn.setFixedSize(140, 110)
        btn.setStyleSheet(
            "QPushButton{background:white;border:2px solid #e2e8f4;border-radius:14px;"
            "font-size:13px;font-weight:600;color:#1e3a5f;"
            "font-family:'Segoe UI','Arial Hebrew',sans-serif;}"
            "QPushButton:hover{background:#eff6ff;border-color:#3b82f6;}"
            "QPushButton:pressed{background:#dbeafe;}"
        )
        btn.clicked.connect(lambda checked=False, exe=exe_name: self._launch(exe))
        return btn

    def _launch(self, exe_name: str):
        """מפעיל תוכנה"""
        try:
            full_path = _find_exe(exe_name)
            if os.path.isabs(full_path) and os.path.exists(full_path):
                subprocess.Popen([full_path])
            else:
                # fallback: shellexecute
                os.startfile(full_path)
        except Exception as e:
            # ניסיון נוסף עם shell=True
            try:
                subprocess.Popen(exe_name, shell=True)
            except Exception:
                pass

    def _tick_clock(self):
        from datetime import datetime
        self._clock.setText(datetime.now().strftime("%H:%M"))

    def _on_logout(self):
        self._clock_timer.stop()
        self.logout_requested.emit()

    def keyPressEvent(self, event):
        # חסום Escape ושאר מקשי יציאה
        if event.key() == Qt.Key.Key_Escape:
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        event.ignore()
